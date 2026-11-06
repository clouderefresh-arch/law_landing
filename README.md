# без-адвоката.рф

Лендинг «Как выиграть суд без адвоката?» — файлы в `site/`.
Живой сайт: https://без-адвоката.рф/

Сейчас на хостинге Reg.ru (ISPmanager, `37.140.192.114`) стоит **самоподписанный** сертификат, поэтому браузер показывает предупреждение. Доверенный Let's Encrypt выпускается так:

```bash
export ISP_USER='логин_панели'
export ISP_PASSWORD='пароль_панели'
python3 deploy/issue-ssl.py
```

Скрипт через API панели (`letsencrypt.generate`) выпускает сертификат на `без-адвоката.рф` и `www`, вешает его на сайт, включает редирект HTTP→HTTPS и HSTS.

Тот же вход, что у панели на порту 1500. Либо секреты `ISP_USER` / `ISP_PASSWORD` в GitHub Actions → workflow «Issue Let's Encrypt».

Запасной nginx-конфиг для своего VPS: `deploy/nginx-bez-advokata.conf`.
