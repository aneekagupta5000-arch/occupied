from pathlib import Path
import zipfile

root = Path(__file__).resolve().parent
exe = root / 'dist' / 'myapp.exe'
readme = root / 'README.txt'
output = root / 'LifeAuditApp.zip'

with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as z:
    z.write(exe, exe.name)
    z.write(readme, readme.name)

print(output.resolve())
