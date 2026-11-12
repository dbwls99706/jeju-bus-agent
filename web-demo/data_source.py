"""Explicit, hash-pinned source selection. Never fetches or publishes data.

Integration:
    raw, metadata = read_source()   # verifies before returning bytes
    # parse raw as UTF-8 BOM CSV in the existing analysis engine

For an existing cached parser, include get_mode() in its cache key and call
verify_bytes(raw, mode) before parsing. Do not reuse a synthetic checksum for
real mode. get_metadata() describes the configured source, not successful IO.
"""
import gzip
import hashlib
import hmac
import os
from pathlib import Path

REAL_SHA256 = 'acecf3fa511c68def3b68c34c29610dbda1101070f38e4be856cdcb123a4a529'
SYNTHETIC_SHA256 = 'f676552326bd5e8c9d6c2d00efd00f9068ad89a1f5efb8bf84c26a075e45369d'
_BASE_DIR = Path(__file__).resolve().parent


class DataSourceError(ValueError):
    """Safe source-configuration or integrity error; no filesystem path leaked."""


def get_mode(mode=None):
    """Return only an explicitly supported mode. Unset env defaults to the published real dataset."""
    value = os.environ.get('DATA_MODE', 'real') if mode is None else mode
    if value not in ('synthetic', 'real'):
        raise DataSourceError('DATA_MODE must be synthetic or real.')
    return value


def source_path(mode=None, *, base_dir=None):
    """Fixed local filename; base_dir is a trusted-code/test hook, never request input."""
    selected = get_mode(mode)
    base = _BASE_DIR if base_dir is None else Path(base_dir)
    return base / 'data' / ('bus.csv.gz' if selected == 'real' else 'synthetic.csv')


def expected_sha256(mode=None):
    return REAL_SHA256 if get_mode(mode) == 'real' else SYNTHETIC_SHA256


def verify_bytes(raw, mode=None):
    """Validate exact known bytes. Return checksum; no silent fallback."""
    selected = get_mode(mode)
    if not isinstance(raw, bytes):
        raise TypeError('Data source must be bytes.')
    actual = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(actual, expected_sha256(selected)):
        raise DataSourceError('Configured data checksum does not match the verified source.')
    return actual


def verify_file(path, mode=None):
    """Verify a trusted local path (supports external original-file QA without copying)."""
    selected = get_mode(mode)
    try:
        raw = read_raw(path)
    except OSError as exc:
        raise DataSourceError('Configured data file is unavailable; fallback is disabled.') from exc
    return verify_bytes(raw, selected)


def get_metadata(mode=None):
    """Public-safe provenance. Does not assert the file is present or AI is enabled."""
    selected = get_mode(mode)
    if selected == 'synthetic':
        return {
            'data_kind': 'synthetic',
            'name': 'synthetic.csv',
            'expected_sha256': SYNTHETIC_SHA256,
            'source_url': '',
            'metadata_url': '',
            'provenance': '절차 체험을 위해 만든 합성 자료. 실제 제주 승차 기록이 아닙니다.',
            'license_status': 'generated_synthetic',
            'license_caveat': '원본 데이터의 이용조건을 대신하지 않습니다.',
            'data_notice': '2024년 1~2월 날짜를 사용한 합성 예시 데이터입니다.',
        }
    return {
        'data_kind': 'real',
        'name': '일별시간대별버스승차인원수현황.csv',
        'expected_sha256': REAL_SHA256,
        'source_url': 'https://www.jejudatahub.net/data/view/data/512',
        'metadata_url': 'https://data.edmgr.kr/dataView.do?id=jejudatahub-net-512',
        'provenance': '사용자 제공 제주 버스 승차 집계 파일. 검증된 원본 SHA-256과 일치하는 파일만 사용합니다.',
        'license_status': 'cc-zero_in_official_secondary_metadata',
        'license_label': 'CC0 (교육부·KERIS 공식 2차 메타데이터 표기)',
        'license_url': 'https://creativecommons.org/publicdomain/zero/1.0/deed.ko',
        'license_caveat': '공식 2차 메타에 동일 데이터명·파일명과 cc-zero가 표시됩니다. 원본 포털은 접속 제한으로 현행 이용조건과 파일 버전 동일성을 대조하지 못했습니다. 이 표기는 원본 공개 재배포 권리의 최종 확인이 아닙니다.',
        'data_notice': '2023-12-25~2025-10-26의 과거 승차 집계이며 실시간 버스 정보가 아닙니다.',
    }


def read_source(mode=None, *, base_dir=None):
    """Read the configured local file exactly once and verify before returning it."""
    selected = get_mode(mode)
    try:
        raw = read_raw(source_path(selected, base_dir=base_dir))
    except OSError as exc:
        raise DataSourceError('Configured data file is unavailable; fallback is disabled.') from exc
    sha = verify_bytes(raw, selected)
    metadata = get_metadata(selected)
    metadata['sha256'] = sha
    return raw, metadata


def read_raw(path):
    """Read fixed local source; decompressed CSV is bounded and hash-verified by caller."""
    path = Path(path)
    if path.suffix == '.gz':
        with gzip.open(path, 'rb') as stream:
            raw = stream.read(2_000_001)
        if len(raw) > 2_000_000:
            raise DataSourceError('Configured data exceeds source size limit.')
        return raw
    return path.read_bytes()
