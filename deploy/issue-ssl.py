#!/usr/bin/env python3
"""Issue a trusted Let's Encrypt certificate for без-адвоката.рф via ISPmanager."""

from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DOMAIN_IDN = "без-адвоката.рф"
DOMAIN_ASCII = "xn----8sbaabinfs8a6byc.xn--p1ai"
WWW_ASCII = f"www.{DOMAIN_ASCII}"
WWW_IDN = f"www.{DOMAIN_IDN}"
EMAIL = os.environ.get("SSL_EMAIL", "nilich1972@mail.ru")
DEFAULT_PANEL = "https://37.140.192.114:1500/ispmgr"
ALT_PANEL = "https://server113.hosting.reg.ru:1500/ispmgr"
CRT_NAME = "bez-advokata-le"
CSR_NAME = "bez-advokata-csr"

INSECURE_SSL = ssl._create_unverified_context()


def die(message: str, code: int = 1) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def request(panel: str, params: dict[str, str]) -> dict[str, Any]:
    query = urllib.parse.urlencode(params)
    url = f"{panel}?{query}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, context=INSECURE_SSL, timeout=60) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        die(f"Панель вернула не JSON:\n{raw[:800]}")
    return data


def doc_error(data: dict[str, Any]) -> str | None:
    err = data.get("doc", {}).get("error")
    if not err:
        return None
    msg = err.get("msg", {})
    if isinstance(msg, dict):
        return str(msg.get("$") or msg)
    return str(err)


def elems(data: dict[str, Any]) -> list[dict[str, Any]]:
    value = data.get("doc", {}).get("elem", [])
    if value is None:
        return []
    if isinstance(value, dict):
        return [value]
    return list(value)


def field(elem: dict[str, Any], name: str) -> str:
    node = elem.get(name, "")
    if isinstance(node, dict):
        return str(node.get("$") or "")
    return str(node or "")


SKIP_FORM_KEYS = {
    "elem",
    "error",
    "ok",
    "warning",
    "messages",
    "slist",
    "metadata",
    "tparams",
}


def form_values(data: dict[str, Any]) -> dict[str, str]:
    values: dict[str, str] = {}
    for key, node in data.get("doc", {}).items():
        if key in SKIP_FORM_KEYS or key.startswith("$"):
            continue
        if "passwd" in key.lower() or "password" in key.lower():
            continue
        if isinstance(node, dict) and "$" in node:
            values[key] = str(node["$"])
        elif isinstance(node, str):
            values[key] = node
    return values


def names_of(elem: dict[str, Any]) -> set[str]:
    found: set[str] = set()
    for key in ("name", "displaykey", "key"):
        value = field(elem, key).strip()
        if value:
            found.add(value)
    return found


def pick_site(rows: list[dict[str, Any]]) -> dict[str, Any]:
    wanted = {DOMAIN_IDN, DOMAIN_ASCII, WWW_IDN, WWW_ASCII}
    for row in rows:
        if names_of(row) & wanted:
            return row
        aliases = field(row, "aliases")
        if any(name in aliases for name in wanted):
            return row
    die(
        "В панели нет сайта без-адвоката.рф. Найдено: "
        + ", ".join(sorted({field(r, "name") for r in rows}) or ["—"])
    )


def issuer_is_trusted() -> tuple[bool, str]:
    import subprocess

    probe = subprocess.run(
        [
            "openssl",
            "s_client",
            "-connect",
            f"{DOMAIN_ASCII}:443",
            "-servername",
            DOMAIN_ASCII,
        ],
        input=b"",
        capture_output=True,
        timeout=20,
        check=False,
    )
    cert = subprocess.run(
        ["openssl", "x509", "-noout", "-issuer", "-subject"],
        input=probe.stdout,
        capture_output=True,
        timeout=10,
        check=False,
    )
    text = cert.stdout.decode("utf-8", errors="replace").strip()
    trusted = any(
        token in text.lower()
        for token in ("let's encrypt", "lets encrypt", "r10", "r11", "r12", "r13", "r14", "isrg")
    )
    return trusted, text or probe.stderr.decode("utf-8", errors="replace")[:400]


def main() -> None:
    user = os.environ.get("ISP_USER", "").strip()
    password = os.environ.get("ISP_PASSWORD", "").strip()
    if not user or not password:
        die(
            "Нужны переменные ISP_USER и ISP_PASSWORD — логин и пароль "
            "хостинга Reg.ru / ISPmanager (те же, что для панели на порту 1500)."
        )

    panel = os.environ.get("ISP_PANEL", DEFAULT_PANEL).rstrip("/")
    authinfo = f"{user}:{password}"

    login = request(
        panel,
        {"out": "json", "func": "auth", "username": user, "password": password},
    )
    login_err = doc_error(login)
    if login_err and "insufficient" not in login_err.lower():
        # Some panels reject func=auth but still accept authinfo on later calls.
        print(f"Прямой вход: {login_err}. Пробую authinfo…")

    sites = request(
        panel,
        {"out": "json", "func": "webdomain", "authinfo": authinfo},
    )
    err = doc_error(sites)
    if err:
        if panel == DEFAULT_PANEL:
            print(f"{panel} отказала: {err}. Пробую запасной адрес панели…")
            panel = ALT_PANEL
            sites = request(
                panel,
                {"out": "json", "func": "webdomain", "authinfo": authinfo},
            )
            err = doc_error(sites)
        if err:
            die(f"Не удалось получить список сайтов: {err}")

    site = pick_site(elems(sites))
    domain_name = field(site, "name") or DOMAIN_ASCII
    username = field(site, "owner") or field(site, "user") or user
    print(f"Сайт в панели: {domain_name}, владелец: {username}")

    generate = request(
        panel,
        {
            "out": "json",
            "func": "letsencrypt.generate",
            "authinfo": authinfo,
            "sok": "ok",
            "domain_name": domain_name,
            "domain": f"{DOMAIN_ASCII} {WWW_ASCII}",
            "email": EMAIL,
            "crtname": CRT_NAME,
            "name": CSR_NAME,
            "username": username,
            "keylen": "2048",
            "wildcard": "off",
            "dns_check": "off",
            "skip_check_a_record": "off",
            "enable_cert": "on",
        },
    )
    gen_err = doc_error(generate)
    if gen_err:
        die(f"Let's Encrypt не выпустился: {gen_err}")
    print("Панель приняла выпуск сертификата Let's Encrypt.")

    current = request(
        panel,
        {
            "out": "json",
            "func": "webdomain.edit",
            "authinfo": authinfo,
            "elid": domain_name,
        },
    )
    current_err = doc_error(current)
    if current_err:
        print(f"Сертификат выпущен, форму сайта не прочитал: {current_err}")
    else:
        payload = form_values(current)
        payload.update(
            {
                "out": "json",
                "func": "webdomain.edit",
                "authinfo": authinfo,
                "sok": "ok",
                "elid": domain_name,
                "secure": "on",
                "ssl_cert": CRT_NAME,
                "redirect_http": "on",
                "hsts": "on",
            }
        )
        redirect = request(panel, payload)
        redir_err = doc_error(redirect)
        if redir_err:
            print(f"Сертификат выпущен, редирект HTTP→HTTPS не включился: {redir_err}")
        else:
            print("Включены HTTPS, редирект с HTTP и HSTS.")

    for attempt in range(1, 9):
        time.sleep(5)
        trusted, details = issuer_is_trusted()
        print(f"Проверка {attempt}: {details}")
        if trusted:
            print(f"Готово. Браузерный HTTPS: https://{DOMAIN_IDN}/")
            return
    die(
        "Панель ответила успехом, но публичный сертификат ещё самоподписанный. "
        "Подождите минуту и запустите скрипт снова — выпуск Let's Encrypt на shared-хостинге бывает отложенным."
    )


if __name__ == "__main__":
    main()
