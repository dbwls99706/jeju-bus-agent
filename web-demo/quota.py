"""Durable global Redis quota reservation, independent of the AI client.

Required env: QUOTA_REDIS_REST_URL, QUOTA_REDIS_REST_TOKEN, QUOTA_NAMESPACE,
QUOTA_LIFETIME_LIMIT, QUOTA_DAILY_LIMIT, QUOTA_MINUTE_LIMIT.
Limits are positive integers with minute <= daily <= lifetime. Namespace is a
stable identifier for ONE global budget, not a deployment, user, IP or session.
Never rotate the namespace, delete/reset its keys, or use an ephemeral Redis
instance during a budget's lifetime. Redis persistence/account retention is an
operator responsibility. A failed or ambiguous reservation is not refunded or
retried. A lost HTTP reply can consume a reservation but cannot permit an AI call.

Usage (not wired to OpenAI here): reserve_call = RedisQuota.from_env().reserve_call
No network calls occur during import or configuration validation.
"""
import ipaddress
import json
import os
import re
from dataclasses import dataclass, field
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

# All three persistent keys share a Redis Cluster hash tag. Redis server TIME,
# not process time, defines UTC epoch-day and epoch-minute buckets. Each check
# and update is performed in one atomic EVAL. No successful reservation expires.
LUA_RESERVE = r'''
local lifetime_limit = tonumber(ARGV[1])
local daily_limit = tonumber(ARGV[2])
local minute_limit = tonumber(ARGV[3])
local function integer(s)
  if not s then return 0 end
  local n = tonumber(s)
  if not n or n < 0 or n ~= math.floor(n) then error('invalid quota state') end
  return n
end
for i=1,3 do
  if redis.call('TTL', KEYS[i]) >= 0 then error('expiring quota state') end
end
local now = redis.call('TIME')
local day = math.floor(tonumber(now[1]) / 86400)
local minute = math.floor(tonumber(now[1]) / 60)
local total = integer(redis.call('GET', KEYS[1]))
local d = redis.call('HMGET', KEYS[2], 'bucket', 'count')
local m = redis.call('HMGET', KEYS[3], 'bucket', 'count')
local db = integer(d[1])
local mb = integer(m[1])
local daily = integer(d[2])
local per_minute = integer(m[2])
if db > day or mb > minute then error('quota clock moved backwards') end
if db ~= day then daily = 0 end
if mb ~= minute then per_minute = 0 end
if total >= lifetime_limit then return {0, 'lifetime'} end
if daily >= daily_limit then return {0, 'daily'} end
if per_minute >= minute_limit then return {0, 'minute'} end
redis.call('INCR', KEYS[1])
redis.call('HSET', KEYS[2], 'bucket', day, 'count', daily + 1)
redis.call('HSET', KEYS[3], 'bucket', minute, 'count', per_minute + 1)
return {1, total + 1, daily + 1, per_minute + 1}
'''


class QuotaUnavailable(ValueError):
    """Safe error containing neither credentials nor provider response details."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise HTTPError(req.full_url, code, 'Redirects disabled', headers, fp)


def _limit(value):
    if not isinstance(value, str) or not re.fullmatch(r'[1-9][0-9]{0,9}', value):
        raise QuotaUnavailable('Quota limits must be positive integers.')
    result = int(value)
    if result > 2147483647:
        raise QuotaUnavailable('Quota limit is out of range.')
    return result


def _url(value):
    try:
        parts = urlsplit(value)
        host = parts.hostname
        if (parts.scheme != 'https' or not host or parts.username is not None
                or parts.password is not None or parts.query or parts.fragment
                or parts.path not in ('', '/') or parts.port not in (None, 443)
                or not re.fullmatch(r'[A-Za-z0-9.-]+', host)
                or '.' not in host or host.endswith('.')
                or host.lower().endswith(('.localhost', '.local', '.internal'))):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError()  # no raw IP/private endpoint configuration
        return 'https://' + host.lower()
    except (ValueError, TypeError):
        raise QuotaUnavailable('A public HTTPS Redis REST origin is required.') from None


@dataclass(frozen=True)
class QuotaConfig:
    url: str
    token: str = field(repr=False)
    namespace: str
    lifetime: int
    daily: int
    minute: int

    @classmethod
    def from_env(cls):
        token = os.environ.get('QUOTA_REDIS_REST_TOKEN', '')
        namespace = os.environ.get('QUOTA_NAMESPACE', '')
        if not token or token != token.strip() or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise QuotaUnavailable('Redis quota credentials are not configured.')
        if not re.fullmatch(r'[A-Za-z0-9_-]{3,64}', namespace):
            raise QuotaUnavailable('A stable global quota namespace is required.')
        life = _limit(os.environ.get('QUOTA_LIFETIME_LIMIT', ''))
        daily = _limit(os.environ.get('QUOTA_DAILY_LIMIT', ''))
        minute = _limit(os.environ.get('QUOTA_MINUTE_LIMIT', ''))
        if not minute <= daily <= life:
            raise QuotaUnavailable('Quota limits must satisfy minute <= daily <= lifetime.')
        return cls(_url(os.environ.get('QUOTA_REDIS_REST_URL', '')), token, namespace, life, daily, minute)


def _post(config, command):
    request = Request(config.url, data=json.dumps(command).encode('utf-8'),
        headers={'Authorization': 'Bearer ' + config.token, 'Content-Type': 'application/json'}, method='POST')
    with build_opener(_NoRedirect()).open(request, timeout=5) as response:
        if response.status != 200:
            raise QuotaUnavailable('Quota service is unavailable.')
        raw = response.read(8193)
    if len(raw) > 8192:
        raise QuotaUnavailable('Quota service returned an invalid response.')
    return json.loads(raw.decode('utf-8'))


class RedisQuota:
    def __init__(self, config):
        # Only from_env produces validated configuration. Validate direct callers
        # again so direct construction cannot loosen the origin or limit checks.
        if not isinstance(config, QuotaConfig):
            raise QuotaUnavailable('Validated quota configuration is required.')
        if (_url(config.url) != config.url or not re.fullmatch(r'[A-Za-z0-9_-]{3,64}', config.namespace)
                or not config.token or config.token != config.token.strip()
                or any(ord(c) < 33 or ord(c) > 126 for c in config.token)
                or any(type(n) is not int or not 1 <= n <= 2147483647 for n in (config.lifetime, config.daily, config.minute))
                or not config.minute <= config.daily <= config.lifetime):
            raise QuotaUnavailable('Quota configuration is invalid.')
        self.config = config

    @classmethod
    def from_env(cls):
        return cls(QuotaConfig.from_env())

    def reserve_call(self):
        c = self.config
        prefix = 'busyeoul:quota:{' + c.namespace + '}'
        command = ['EVAL', LUA_RESERVE, '3', prefix + ':lifetime', prefix + ':daily', prefix + ':minute',
                   str(c.lifetime), str(c.daily), str(c.minute)]
        try:
            response = _post(c, command)
            if not isinstance(response, dict) or response.get('error') or set(response) != {'result'}:
                raise ValueError()
            result = response['result']
            if (isinstance(result, list) and len(result) == 2 and type(result[0]) is int
                    and result[0] == 0 and result[1] in ('lifetime', 'daily', 'minute')):
                return False
            if (not isinstance(result, list) or len(result) != 4 or any(type(n) is not int for n in result)
                    or result[0] != 1 or not 1 <= result[3] <= c.minute
                    or not 1 <= result[2] <= c.daily or not 1 <= result[1] <= c.lifetime
                    or not result[3] <= result[2] <= result[1]):
                raise ValueError()
            return True
        except Exception:
            raise QuotaUnavailable('AI 호출 한도를 확인할 수 없어 요청하지 않았습니다.') from None
