# без-адвоката.рф

Лендинг «Как выиграть суд без адвоката?» — файлы в `site/`.
Живой сайт: https://без-адвоката.рф/

На хостинге Reg.ru сейчас **самоподписанный** SSL, браузер показывает предупреждение.

**Как выпустить Let’s Encrypt:** пошаговый туториал в [docs/ssl-tutorial.md](docs/ssl-tutorial.md) (клики в ISPmanager, без SSH).

Скрипт того же выпуска:

```bash
export ISP_USER='логин_панели'
export ISP_PASSWORD='пароль_панели'
python3 deploy/issue-ssl.py
```
