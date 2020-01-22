# UDP File Transfer
Program python yang digunakan untuk mengirim file melalui Internet pada jaringan yang sama dengan protokol UDP.<br><br>
Program dapat mengirimkan satu atau lebih file selama ada koneksi jaringan yang stabil.
## Running 
```bash
python app.py
```
## Input
- Pertama kali masukan port yang akan digunakan penrima untuk menerima file
- `send <file> <ip>`: mengirimkan `<file>` kepada penerima di `<ip>` yang didapat pada jaringan yang sama 
- `show`: menampilkan progress pengirimanf file sekarang
- `quit`: keluar dari program
- `help`: menampilkan daftar <i>command</i> yang tersedia