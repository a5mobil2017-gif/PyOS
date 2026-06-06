#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║           PyOS Builder — Bootovatelný Linux ISO Tvůrce           ║
║         Pro 64-bit AMD Ryzen 7 + AMD GPU (VirtualBox ready)      ║
║         Podporuje: RHEL / CentOS / Rocky / Fedora / Debian       ║
╚══════════════════════════════════════════════════════════════════╝

Tento skript vytvoří plně bootovatelný Linux ISO s grafickým UI.
Podporuje: VirtualBox, QEMU, fyzický USB boot

POUŽITÍ:
  sudo python3 build_os.py

Výsledek: ./PyOS-1.0-amd64.iso  (~800 MB)
"""

import os
import sys
import subprocess
import shutil
import time
import platform
from pathlib import Path

# ─────────────────────────────────────────────
#  KONFIGURACE
# ─────────────────────────────────────────────
CONFIG = {
    "os_name":        "PyOS",
    "os_version":     "1.0",
    "os_codename":    "Amber",
    "arch":           "amd64",
    "hostname":       "pyos",
    "username":       "user",
    "password":       "pyos123",
    "root_password":  "root",
    "locale":         "cs_CZ.UTF-8",
    "timezone":       "Europe/Prague",
    "keyboard":       "cz",
    "debian_mirror":  "http://deb.debian.org/debian",
    "debian_suite":   "bookworm",
    "desktop":        "xfce4",
    "work_dir":       "/tmp/pyos_build",
    "output_iso":     "./PyOS-1.0-amd64.iso",
    "colors": {
        "header":  "\033[95m",
        "blue":    "\033[94m",
        "cyan":    "\033[96m",
        "green":   "\033[92m",
        "yellow":  "\033[93m",
        "red":     "\033[91m",
        "bold":    "\033[1m",
        "end":     "\033[0m",
    }
}

C = CONFIG["colors"]

# ─────────────────────────────────────────────
#  DETEKCE OS HOSTITELE
# ─────────────────────────────────────────────
def detect_host_os():
    """
    Detekuje jestli běžíme na Red Hat rodině nebo Debian rodině.
    Vrací: 'redhat' | 'debian' | 'unknown'
    """
    # Zkusit /etc/os-release
    os_release = Path("/etc/os-release")
    if os_release.exists():
        content = os_release.read_text().lower()
        # Red Hat rodina
        if any(x in content for x in [
            "rhel", "red hat", "centos", "rocky", "almalinux",
            "fedora", "oracle linux", "scientific linux"
        ]):
            return "redhat"
        # Debian rodina
        if any(x in content for x in ["debian", "ubuntu", "mint", "pop"]):
            return "debian"

    # Fallback — zkusit příkazy
    if shutil.which("dnf") or shutil.which("yum"):
        return "redhat"
    if shutil.which("apt-get"):
        return "debian"

    return "unknown"


def get_redhat_variant():
    """Vrátí konkrétní variantu Red Hat OS (fedora / rhel / centos atd.)"""
    os_release = Path("/etc/os-release")
    if os_release.exists():
        content = os_release.read_text().lower()
        if "fedora" in content:
            return "fedora"
        if "centos" in content:
            return "centos"
        if "rocky" in content:
            return "rocky"
        if "almalinux" in content:
            return "alma"
        if "red hat" in content or "rhel" in content:
            return "rhel"
    return "rhel"  # výchozí


def get_pkg_manager():
    """Vrátí správný package manager pro aktuální OS."""
    if shutil.which("dnf"):
        return "dnf"
    if shutil.which("yum"):
        return "yum"
    if shutil.which("apt-get"):
        return "apt-get"
    return None

# ─────────────────────────────────────────────
#  POMOCNÉ FUNKCE
# ─────────────────────────────────────────────
def banner():
    host_os  = detect_host_os()
    variant  = get_redhat_variant() if host_os == "redhat" else host_os
    os_label = {
        "redhat":  f"{C['red']}Red Hat{C['end']}",
        "fedora":  f"{C['red']}Fedora{C['end']}",
        "centos":  f"{C['yellow']}CentOS{C['end']}",
        "rocky":   f"{C['green']}Rocky Linux{C['end']}",
        "alma":    f"{C['cyan']}AlmaLinux{C['end']}",
        "rhel":    f"{C['red']}RHEL{C['end']}",
        "debian":  f"{C['blue']}Debian/Ubuntu{C['end']}",
    }.get(variant, variant)

    print(f"""
{C['cyan']}{C['bold']}
 ██████╗ ██╗   ██╗ ██████╗ ███████╗
 ██╔══██╗╚██╗ ██╔╝██╔═══██╗██╔════╝
 ██████╔╝ ╚████╔╝ ██║   ██║███████╗
 ██╔═══╝   ╚██╔╝  ██║   ██║╚════██║
 ██║        ██║   ╚██████╔╝███████║
 ╚═╝        ╚═╝    ╚═════╝ ╚══════╝
     {C['yellow']}B U I L D E R  v2.0{C['end']}
{C['cyan']} ──────────────────────────────────────
 Bootovatelný Linux ISO tvůrce
 AMD Ryzen 7 + AMD GPU optimized
 Target: VirtualBox / USB boot
 Hostitelský OS: {os_label}
 ──────────────────────────────────────{C['end']}
""")


def log(msg, level="info"):
    icons = {"info": "ℹ", "ok": "✓", "warn": "⚠", "err": "✗",
             "step": "▶", "build": "⚙", "detect": "🔍"}
    colors_map = {
        "info": C['blue'], "ok": C['green'], "warn": C['yellow'],
        "err": C['red'],   "step": C['cyan'], "build": C['header'],
        "detect": C['yellow'],
    }
    icon  = icons.get(level, "•")
    color = colors_map.get(level, "")
    ts    = time.strftime("%H:%M:%S")
    print(f"  {color}{C['bold']}[{ts}] {icon}  {msg}{C['end']}")


def run(cmd, check=True, capture=False, chroot=None):
    """Spustí shell příkaz, volitelně uvnitř chroot."""
    if chroot:
        cmd = f"chroot {chroot} /bin/bash -c {repr(cmd)}"
    if capture:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return r.stdout.strip()
    else:
        result = subprocess.run(cmd, shell=True)
        if check and result.returncode != 0:
            log(f"Příkaz selhal: {cmd}", "err")
            sys.exit(1)
        return result.returncode


def check_root():
    if os.geteuid() != 0:
        log("Skript musí být spuštěn jako root: sudo python3 build_os.py", "err")
        sys.exit(1)


# ─────────────────────────────────────────────
#  KROK 0: KONTROLA A INSTALACE ZÁVISLOSTÍ
#          — Red Hat i Debian větev
# ─────────────────────────────────────────────
def check_dependencies():
    log("Detekuji hostitelský OS...", "detect")

    host_os = detect_host_os()
    pkg_mgr = get_pkg_manager()

    if host_os == "unknown" or pkg_mgr is None:
        log("Nepodporovaný OS nebo nenalezen package manager!", "err")
        log("Podporovány: RHEL, CentOS, Rocky, AlmaLinux, Fedora, Debian, Ubuntu", "info")
        sys.exit(1)

    log(f"Hostitelský OS: {host_os.upper()}  |  Package manager: {pkg_mgr}", "ok")

    # ── Větev RED HAT ────────────────────────────────────────────────────────
    if host_os == "redhat":
        _install_deps_redhat(pkg_mgr)

    # ── Větev DEBIAN ─────────────────────────────────────────────────────────
    else:
        _install_deps_debian()

    log("Všechny závislosti jsou připraveny.", "ok")


def _install_deps_redhat(pkg_mgr):
    """Instaluje závislosti na Red Hat rodině (RHEL/CentOS/Rocky/Fedora)."""
    log("Instaluji závislosti pro Red Hat OS...", "step")
    variant = get_redhat_variant()

    # ── 1. EPEL repozitář (potřebný pro debootstrap a další) ─────────────────
    if not shutil.which("debootstrap"):
        log("Přidávám EPEL repozitář...", "info")
        if variant == "fedora":
            # Fedora nepotřebuje EPEL — debootstrap je v main repo
            run(f"{pkg_mgr} install -y debootstrap", check=False)
        else:
            # RHEL / CentOS / Rocky / Alma — nejprve EPEL
            run(f"{pkg_mgr} install -y epel-release", check=False)
            # Pro RHEL 8/9 aktivovat CodeReady Builder
            run("subscription-manager repos --enable codeready-builder-for-rhel-9-x86_64-rpms 2>/dev/null || true",
                check=False)
            # Rocky/Alma ekvivalent CRB
            run(f"{pkg_mgr} config-manager --set-enabled crb 2>/dev/null || "
                f"{pkg_mgr} config-manager --set-enabled PowerTools 2>/dev/null || true",
                check=False)
            run(f"{pkg_mgr} install -y epel-release", check=False)
            run(f"{pkg_mgr} install -y debootstrap", check=False)

    # ── 2. Základní build nástroje ───────────────────────────────────────────
    redhat_packages = [
        "debootstrap",          # stavba Debian chroot na Red Hat hostu
        "squashfs-tools",       # mksquashfs
        "xorriso",              # tvorba ISO
        "grub2-tools",          # grub-mkimage, grub-mkrescue
        "grub2-tools-extra",    # grub-mkrescue (extra balíček na RHEL)
        "grub2-efi-x64-modules",# EFI moduly pro GRUB
        "grub2-pc-modules",     # BIOS moduly pro GRUB
        "mtools",               # mcopy, mformat
        "dosfstools",           # mkfs.vfat / mkfs.msdos
        "util-linux",           # mount, losetup
        "coreutils",            # dd, cp, mv
        "binutils",             # objcopy (pro EFI)
        "wget",                 # stahování
        "curl",                 # stahování
        "tar",                  # archivy
        "gzip",                 # komprese
        "xz",                   # xz komprese pro squashfs
        "findutils",            # find
        "which",                # which
    ]

    log("Instaluji balíčky (může trvat pár minut)...", "build")
    pkgs = " ".join(redhat_packages)
    run(f"{pkg_mgr} install -y {pkgs}")

    # ── 3. Alternativa pokud debootstrap stále chybí ──────────────────────────
    if not shutil.which("debootstrap"):
        log("debootstrap nenalezen v repozitáři, stahuji přímo...", "warn")
        _install_debootstrap_manual()

    # ── 4. Ověřit grub-mkrescue (název se liší na RH) ────────────────────────
    # Na Red Hat se jmenuje grub2-mkrescue místo grub-mkrescue
    if not shutil.which("grub-mkrescue") and shutil.which("grub2-mkrescue"):
        log("Vytvářím symlink grub-mkrescue → grub2-mkrescue", "info")
        run("ln -sf $(which grub2-mkrescue) /usr/local/bin/grub-mkrescue", check=False)

    if not shutil.which("grub-mkimage") and shutil.which("grub2-mkimage"):
        log("Vytvářím symlink grub-mkimage → grub2-mkimage", "info")
        run("ln -sf $(which grub2-mkimage) /usr/local/bin/grub-mkimage", check=False)

    log("Red Hat závislosti nainstalovány.", "ok")


def _install_debootstrap_manual():
    """
    Stáhne a nainstaluje debootstrap přímo z Debian repozitáře.
    Používá se jako fallback když EPEL debootstrap není dostupný.
    """
    log("Manuální instalace debootstrap z Debian mirrors...", "warn")
    tmp = "/tmp/debootstrap_install"
    os.makedirs(tmp, exist_ok=True)

    # Stáhnout debootstrap .deb a rozbalit
    deb_url = "http://ftp.debian.org/debian/pool/main/d/debootstrap/debootstrap_1.0.132_all.deb"
    deb_path = f"{tmp}/debootstrap.deb"

    try:
        import urllib.request
        log(f"Stahuji: {deb_url}", "info")
        urllib.request.urlretrieve(deb_url, deb_path)

        # Rozbalit .deb (ar archiv) — bez dpkg (není na RH)
        run(f"cd {tmp} && ar x {deb_path}")
        run(f"cd {tmp} && tar -xf data.tar.* -C /")
        run("chmod +x /usr/sbin/debootstrap")
        log("debootstrap nainstalován manuálně.", "ok")
    except Exception as e:
        log(f"Manuální instalace selhala: {e}", "err")
        log("Zkuste: sudo dnf install -y epel-release && sudo dnf install -y debootstrap", "info")
        sys.exit(1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _install_deps_debian():
    """Instaluje závislosti na Debian/Ubuntu."""
    log("Instaluji závislosti pro Debian/Ubuntu...", "step")
    run("apt-get update -qq")
    pkgs = (
        "debootstrap squashfs-tools xorriso "
        "grub-pc-bin grub-efi-amd64-bin grub-common "
        "mtools dosfstools"
    )
    run(f"apt-get install -y -qq {pkgs}")


# ─────────────────────────────────────────────
#  KROK 1: PŘIPRAVIT ADRESÁŘOVOU STRUKTURU
# ─────────────────────────────────────────────
def setup_dirs():
    log("Připravuji adresářovou strukturu...", "step")
    wd = CONFIG["work_dir"]
    dirs = [
        f"{wd}/chroot",
        f"{wd}/image/live",
        f"{wd}/image/isolinux",
        f"{wd}/image/boot/grub",
        f"{wd}/image/EFI/boot",
        f"{wd}/staging",
    ]
    if os.path.exists(wd):
        log("Čistím předchozí build...", "warn")
        run(f"umount -lf {wd}/chroot/proc {wd}/chroot/sys "
            f"{wd}/chroot/dev/pts {wd}/chroot/dev 2>/dev/null || true",
            check=False)
        shutil.rmtree(wd, ignore_errors=True)

    for d in dirs:
        os.makedirs(d, exist_ok=True)
    log("Adresářová struktura připravena.", "ok")


# ─────────────────────────────────────────────
#  KROK 2: DEBOOTSTRAP — základ Debian systému
# ─────────────────────────────────────────────
def run_debootstrap():
    log("Stahuji základní Debian systém (debootstrap)...", "step")
    log(f"  Mirror: {CONFIG['debian_mirror']}", "info")
    log(f"  Suite:  {CONFIG['debian_suite']} ({CONFIG['arch']})", "info")

    chroot = f"{CONFIG['work_dir']}/chroot"
    mirror = CONFIG["debian_mirror"]
    suite  = CONFIG["debian_suite"]
    arch   = CONFIG["arch"]

    # Na Red Hat může být debootstrap v /usr/sbin
    dbs = shutil.which("debootstrap") or "/usr/sbin/debootstrap"
    if not os.path.exists(dbs):
        log("debootstrap nenalezen! Zkontroluj instalaci.", "err")
        sys.exit(1)

    # Debootstrap s keyring fallback (RH nemá debian-keyring)
    host_os = detect_host_os()
    if host_os == "redhat":
        log("Red Hat host: používám --no-check-gpg pro debootstrap", "warn")
        run(f"{dbs} --arch={arch} --variant=minbase --no-check-gpg "
            f"{suite} {chroot} {mirror}")
    else:
        run(f"{dbs} --arch={arch} --variant=minbase {suite} {chroot} {mirror}")

    log("Debootstrap dokončen.", "ok")


# ─────────────────────────────────────────────
#  KROK 3: KONFIGURACE SYSTÉMU UVNITŘ CHROOT
# ─────────────────────────────────────────────
def configure_system():
    log("Konfiguruju systém uvnitř chroot...", "step")
    wd     = CONFIG["work_dir"]
    chroot = f"{wd}/chroot"

    run(f"mount --bind /dev     {chroot}/dev")
    run(f"mount --bind /dev/pts {chroot}/dev/pts")
    run(f"mount -t proc  proc   {chroot}/proc")
    run(f"mount -t sysfs sysfs  {chroot}/sys")

    _write_chroot_setup(chroot)

    log("Instaluji balíčky uvnitř chroot (trvá ~10–20 min)...", "build")
    run(f"chroot {chroot} /bin/bash /tmp/setup.sh")

    run(f"umount -lf {chroot}/proc {chroot}/sys {chroot}/dev/pts {chroot}/dev",
        check=False)
    log("Systémová konfigurace dokončena.", "ok")


def _write_chroot_setup(chroot):
    """Zapíše setup.sh dovnitř chroot filesystému (vždy Debian uvnitř)."""
    name     = CONFIG["os_name"]
    hostname = CONFIG["hostname"]
    user     = CONFIG["username"]
    passwd   = CONFIG["password"]
    rootpw   = CONFIG["root_password"]
    locale   = CONFIG["locale"]
    tz       = CONFIG["timezone"]
    desktop  = CONFIG["desktop"]

    # Uvnitř chroot je vždy Debian — používáme apt
    setup_script = f"""#!/bin/bash
set -e
export DEBIAN_FRONTEND=noninteractive
export LANG=C

echo "{hostname}" > /etc/hostname
cat > /etc/hosts << 'HOSTS'
127.0.0.1   localhost
127.0.1.1   {hostname}
::1         localhost ip6-localhost ip6-loopback
HOSTS

# ── APT sources ──────────────────────────────
cat > /etc/apt/sources.list << 'SOURCES'
deb http://deb.debian.org/debian bookworm main contrib non-free non-free-firmware
deb http://security.debian.org/debian-security bookworm-security main contrib non-free
deb http://deb.debian.org/debian bookworm-updates main contrib non-free
SOURCES

apt-get update -qq

# ── Locale a Timezone ────────────────────────
apt-get install -y locales tzdata
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
echo "{locale} UTF-8" >> /etc/locale.gen
locale-gen
update-locale LANG=en_US.UTF-8
ln -sf /usr/share/zoneinfo/{tz} /etc/localtime
echo "{tz}" > /etc/timezone
dpkg-reconfigure -f noninteractive tzdata

# ── Kernel a live-boot ───────────────────────
apt-get install -y linux-image-amd64 live-boot systemd-sysv

# ── Síť ─────────────────────────────────────
apt-get install -y network-manager net-tools curl wget

# ── Desktop ({desktop}) ──────────────────────
apt-get install -y --no-install-recommends \\
    {desktop} \\
    lightdm lightdm-gtk-greeter \\
    xorg \\
    xserver-xorg-video-amdgpu \\
    xserver-xorg-video-radeon \\
    xserver-xorg-video-vesa \\
    xserver-xorg-input-libinput \\
    pulseaudio pavucontrol \\
    fonts-liberation fonts-dejavu \\
    bash-completion sudo nano htop \\
    thunar mousepad ristretto \\
    firefox-esr \\
    xfce4-terminal || true

# ── AMD GPU firmware ─────────────────────────
apt-get install -y firmware-amd-graphics \\
    mesa-vulkan-drivers libgl1-mesa-dri 2>/dev/null || true

# ── Systémové nástroje ────────────────────────
apt-get install -y gparted galculator evince 2>/dev/null || true

# ── Uživatel ─────────────────────────────────
id -u {user} &>/dev/null || useradd -m -s /bin/bash -G sudo,audio,video,plugdev,netdev {user}
echo "{user}:{passwd}" | chpasswd
echo "root:{rootpw}" | chpasswd

# ── LightDM autologin ─────────────────────────
mkdir -p /etc/lightdm/lightdm.conf.d
cat > /etc/lightdm/lightdm.conf.d/50-autologin.conf << 'LDM'
[Seat:*]
autologin-user={user}
autologin-user-timeout=0
LDM

echo "{user} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/live-user

# ── Desktop obsah ─────────────────────────────
mkdir -p /home/{user}/Desktop /home/{user}/Dokumenty

cat > /home/{user}/Desktop/O_systemu.txt << 'README'
Vítejte v systému {name} {CONFIG["os_version"]}!
=========================================
Tento OS byl sestaven Python skriptem PyOS Builder v2.0
Postaven na hostiteli: Red Hat / Debian kompatibilní

Přihlášení:
  Uživatel: {user}
  Heslo:    {passwd}
  Root pw:  {rootpw}

Desktopové prostředí: {desktop}
Kernel: Linux (Debian Bookworm)
README

chown -R {user}:{user} /home/{user}

# ── Services ──────────────────────────────────
systemctl enable lightdm 2>/dev/null || true
systemctl enable NetworkManager 2>/dev/null || true

# ── Cleanup ───────────────────────────────────
apt-get autoremove -y -qq
apt-get clean
rm -rf /var/lib/apt/lists/*
rm -f /tmp/setup.sh
echo "=== Chroot setup dokoncen ==="
"""

    setup_path = os.path.join(chroot, "tmp", "setup.sh")
    with open(setup_path, "w") as f:
        f.write(setup_script)
    os.chmod(setup_path, 0o755)


# ─────────────────────────────────────────────
#  KROK 4: SQUASHFS
# ─────────────────────────────────────────────
def create_squashfs():
    log("Vytvářím komprimovaný squashfs obraz...", "step")
    wd     = CONFIG["work_dir"]
    chroot = f"{wd}/chroot"
    sqfs   = f"{wd}/image/live/filesystem.squashfs"

    run(f"mksquashfs {chroot} {sqfs} -comp xz -e boot -noappend")
    size_mb = os.path.getsize(sqfs) // (1024 * 1024)
    log(f"Squashfs vytvořen: {size_mb} MB", "ok")


# ─────────────────────────────────────────────
#  KROK 5: KERNEL + INITRD
# ─────────────────────────────────────────────
def copy_kernel():
    log("Kopíruji kernel a initrd...", "step")
    wd     = CONFIG["work_dir"]
    chroot = f"{wd}/chroot"
    boot   = f"{wd}/image/live"

    vmlinuz = sorted(Path(f"{chroot}/boot").glob("vmlinuz-*"))
    initrd  = sorted(Path(f"{chroot}/boot").glob("initrd.img-*"))

    if not vmlinuz or not initrd:
        log("Kernel nebo initrd nenalezen v chroot!", "err")
        sys.exit(1)

    shutil.copy(str(vmlinuz[-1]), f"{boot}/vmlinuz")
    shutil.copy(str(initrd[-1]),  f"{boot}/initrd.img")
    log(f"Kernel: {vmlinuz[-1].name}", "ok")
    log(f"Initrd: {initrd[-1].name}", "ok")


# ─────────────────────────────────────────────
#  KROK 6: GRUB BOOTLOADER
# ─────────────────────────────────────────────
def setup_grub():
    log("Nastavuji GRUB bootloader (BIOS + UEFI)...", "step")
    wd   = CONFIG["work_dir"]
    name = CONFIG["os_name"]
    ver  = CONFIG["os_version"]

    grub_cfg = f"""
set default=0
set timeout=5

insmod all_video
insmod gfxterm
insmod png

terminal_output gfxterm

set menu_color_normal=cyan/black
set menu_color_highlight=white/cyan

menuentry "{name} {ver} — Live Boot (AMD Ryzen 7)" {{
    linux  /live/vmlinuz boot=live quiet splash \\
           amdgpu.dc=1 amdgpu.dpm=1 \\
           radeon.si_support=0 amdgpu.si_support=1 \\
           radeon.cik_support=0 amdgpu.cik_support=1 \\
           console=tty1 loglevel=3
    initrd /live/initrd.img
}}

menuentry "{name} {ver} — Bezpecny rezim (nomodeset)" {{
    linux  /live/vmlinuz boot=live nomodeset quiet splash
    initrd /live/initrd.img
}}

menuentry "{name} {ver} — Debug (verbose)" {{
    linux  /live/vmlinuz boot=live
    initrd /live/initrd.img
}}

menuentry "Vypnout pocitac" {{
    halt
}}

menuentry "Restartovat" {{
    reboot
}}
"""
    grub_dir = f"{wd}/image/boot/grub"
    with open(f"{grub_dir}/grub.cfg", "w") as f:
        f.write(grub_cfg)

    # ISOLINUX fallback
    isolinux_cfg = f"""
DEFAULT live
LABEL live
  MENU LABEL {name} {ver} Live
  KERNEL /live/vmlinuz
  APPEND initrd=/live/initrd.img boot=live quiet splash
TIMEOUT 50
"""
    iso_dir = f"{wd}/image/isolinux"
    with open(f"{iso_dir}/isolinux.cfg", "w") as f:
        f.write(isolinux_cfg)

    # Zkopírovat isolinux.bin (různé cesty na RH vs Debian)
    isolinux_paths = [
        "/usr/lib/ISOLINUX/isolinux.bin",
        "/usr/share/syslinux/isolinux.bin",
        "/usr/lib/syslinux/isolinux.bin",
    ]
    ldlinux_paths = [
        "/usr/lib/syslinux/modules/bios/ldlinux.c32",
        "/usr/share/syslinux/ldlinux.c32",
        "/usr/lib/ISOLINUX/ldlinux.c32",
    ]
    for src in isolinux_paths:
        if os.path.exists(src):
            shutil.copy(src, iso_dir)
            log(f"isolinux.bin zkopírován z {src}", "ok")
            break
    for src in ldlinux_paths:
        if os.path.exists(src):
            shutil.copy(src, iso_dir)
            break

    log("GRUB konfigurace zapsána.", "ok")


# ─────────────────────────────────────────────
#  KROK 7: SESTAVENÍ ISO
# ─────────────────────────────────────────────
def build_iso():
    log("Sestavuji finální ISO obraz...", "step")
    wd      = CONFIG["work_dir"]
    output  = CONFIG["output_iso"]
    name    = CONFIG["os_name"]
    ver     = CONFIG["os_version"]
    img_dir = f"{wd}/image"

    # Najít grub-mkrescue (na RH se jmenuje grub2-mkrescue)
    grub_cmd = (
        shutil.which("grub-mkrescue") or
        shutil.which("grub2-mkrescue")
    )

    if grub_cmd:
        log(f"Používám {os.path.basename(grub_cmd)} pro hybridní ISO (BIOS+UEFI)...", "info")
        run(f'{grub_cmd} -o "{output}" "{img_dir}" '
            f'-- -volid "{name}-{ver}" 2>/dev/null')
    else:
        log("grub-mkrescue nenalezen, používám xorriso přímo...", "warn")
        _build_iso_xorriso(wd, output, name, ver, img_dir)

    if os.path.exists(output):
        size_mb = os.path.getsize(output) // (1024 * 1024)
        log(f"ISO vytvořen: {output} ({size_mb} MB)", "ok")
    else:
        log("ISO soubor nebyl vytvořen!", "err")
        sys.exit(1)


def _build_iso_xorriso(wd, output, name, ver, img_dir):
    """Sestaví ISO přímo pomocí xorriso bez grub-mkrescue."""
    efi_img = f"{wd}/efi.img"
    run(f"dd if=/dev/zero of={efi_img} bs=1M count=4")

    # mkfs.msdos nebo mkfs.vfat (různé názvy)
    mkfs = shutil.which("mkfs.msdos") or shutil.which("mkfs.vfat") or "mkfs.fat"
    run(f"{mkfs} -F 12 {efi_img}")
    run(f"mcopy -si {efi_img} {img_dir}/EFI ::", check=False)

    xorriso_cmd = (
        f'xorriso -as mkisofs '
        f'-iso-level 3 '
        f'-volid "{name}-{ver}" '
        f'-full-iso9660-filenames '
        f'-R -J --joliet-long '
    )
    if os.path.exists(f"{img_dir}/isolinux/isolinux.bin"):
        xorriso_cmd += (
            f'-b isolinux/isolinux.bin '
            f'-no-emul-boot -boot-load-size 4 -boot-info-table '
            f'--eltorito-catalog isolinux/boot.cat '
        )
    if os.path.exists(efi_img):
        xorriso_cmd += (
            f'-eltorito-alt-boot '
            f'-e --interval:appended_partition_2:all:: '
            f'-no-emul-boot '
            f'--append_partition 2 0xef {efi_img} '
        )
    xorriso_cmd += f'-output "{output}" "{img_dir}"'
    run(xorriso_cmd)


# ─────────────────────────────────────────────
#  KROK 8: VÝSLEDNÉ POKYNY
# ─────────────────────────────────────────────
def print_virtualbox_guide():
    output  = CONFIG["output_iso"]
    user    = CONFIG["username"]
    passwd  = CONFIG["password"]
    name    = CONFIG["os_name"]
    host_os = detect_host_os()

    host_label = (
        f"{C['red']}Red Hat / CentOS / Rocky / Fedora{C['end']}"
        if host_os == "redhat"
        else f"{C['blue']}Debian / Ubuntu{C['end']}"
    )

    print(f"""
{C['cyan']}{C['bold']}
╔══════════════════════════════════════════════════════════════════════╗
║                  ISO SESTAVEN ÚSPĚŠNĚ!  v2.0                        ║
╚══════════════════════════════════════════════════════════════════════╝{C['end']}

{C['green']}{C['bold']}ISO soubor:{C['end']} {output}
{C['green']}{C['bold']}Postaven na:{C['end']} {host_label}

{C['yellow']}{C['bold']}══ NASTAVENÍ VIRTUALBOXU ══════════════════════════════════════════════{C['end']}

  1. Otevři VirtualBox → Nový
  2. Jméno: {name}
  3. Typ: Linux → Debian (64-bit)
  4. RAM: min. 2048 MB (doporučeno 4096 MB)
  5. Disk: 20 GB (dynamicky alokovaný)

  {C['cyan']}Systém:{C['end']}
    ✓ Enable I/O APIC
    ✓ Procesor: 2–4 jádra
    ✓ Boot pořadí: Optická mechanika → Hard Disk

  {C['cyan']}Displej:{C['end']}
    ✓ Video paměť: 128 MB
    ✓ Grafický kontroler: VMSVGA nebo VBoxSVGA
    ✓ 3D Acceleration: zapnout

  {C['cyan']}Úložiště:{C['end']}
    ✓ Přidat optický disk → vybrat: {output}

  {C['cyan']}Síť:{C['end']}
    ✓ NAT nebo Bridged Adapter

  6. Spustit → nabootuje do XFCE desktopu!

{C['yellow']}{C['bold']}══ PŘIHLÁŠENÍ ══════════════════════════════════════════════════════════{C['end']}

  Uživatel: {C['green']}{user}{C['end']}
  Heslo:    {C['green']}{passwd}{C['end']}

{C['yellow']}{C['bold']}══ USB BOOT ════════════════════════════════════════════════════════════{C['end']}

  sudo dd if={output} of=/dev/sdX bs=4M status=progress oflag=sync

{C['yellow']}{C['bold']}══ QEMU TEST ═══════════════════════════════════════════════════════════{C['end']}

  qemu-system-x86_64 -m 2048 -cdrom {output} -boot d \\
    -cpu host -enable-kvm -vga virtio -display sdl

{C['cyan']}{C['bold']}══════════════════════════════════════════════════════════════════════{C['end']}
""")


# ─────────────────────────────────────────────
#  HLAVNÍ FUNKCE
# ─────────────────────────────────────────────
def main():
    banner()
    check_root()

    steps = [
        ("Detekce OS a instalace závislostí",  check_dependencies),
        ("Příprava adresářů",                  setup_dirs),
        ("Stažení základního systému",         run_debootstrap),
        ("Konfigurace systému v chroot",       configure_system),
        ("Vytvoření squashfs obrazu",          create_squashfs),
        ("Kopírování kernelu a initrd",        copy_kernel),
        ("Nastavení GRUB bootloaderu",         setup_grub),
        ("Sestavení ISO",                      build_iso),
    ]

    total = len(steps)
    for i, (label, func) in enumerate(steps, 1):
        print(f"\n{C['bold']}{C['yellow']}[{i}/{total}] {label}...{C['end']}")
        start = time.time()
        func()
        elapsed = time.time() - start
        log(f"Hotovo za {elapsed:.1f}s", "ok")

    print_virtualbox_guide()


if __name__ == "__main__":
    main()
