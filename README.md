# без-адвоката.рф

Лендинг «Как выиграть суд без адвоката?» — файлы в `site/`.
Живой сайт: https://без-адвоката.рф/

HTTPS живой: [без-адвоката.рф](https://без-адвоката.рф/) — Let’s Encrypt до 4 февраля 2027, HTTP уходит на HTTPS, HSTS включён. Панель продлевает сертификат сама.

Туториал на случай повторного выпуска: [docs/ssl-tutorial.md](docs/ssl-tutorial.md).

Скрипт того же выпуска:

```bash
export ISP_USER='логин_панели'
export ISP_PASSWORD='пароль_панели'
python3 deploy/issue-ssl.py
```
