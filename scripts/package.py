from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
root=Path(__file__).resolve().parents[1]
out=root.parent/'jeju-bus-guide-review-20261112.zip'
with ZipFile(out,'w',ZIP_DEFLATED) as z:
 for f in root.rglob('*'):
  rel=f.relative_to(root)
  if f.is_file() and not any(p in rel.parts for p in ('.git','.venv','.venv-ai','__pycache__','models','tmp','data')) and f.name!='make_proposal.py' and not (rel.parts[0]=='research' and f.suffix.lower() in ('.png','.jpg','.jpeg','.webp','.gif')):z.write(f,Path('jeju-bus-guide')/rel)
print(out,out.stat().st_size)

full=root.parent/'jeju-bus-guide-submission-prep-20261112.zip'
with ZipFile(full,'w',ZIP_DEFLATED) as z:
 for f in root.rglob('*'):
  rel=f.relative_to(root)
  if f.is_file() and not any(p in rel.parts for p in ('.git','.venv','.venv-ai','__pycache__','models','tmp')) and f.name!='make_proposal.py' and not (rel.parts[0]=='research' and f.suffix.lower() in ('.png','.jpg','.jpeg','.webp','.gif')):z.write(f,Path('jeju-bus-guide')/rel)
print(full,full.stat().st_size)
