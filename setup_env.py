from utils import *

# keep system running with the lid closed
add_content("/etc/systemd/logind.conf", "HandleLidSwitch=ignore")
add_content("/etc/systemd/logind.conf", "LidSwitchIgnoreInhibited=no")
add_content("/etc/needrestart/needrestart.conf", "$nrconf{restart} = 'a'")

# update to latest env
execute_sudo_apt("update")
execute_sudo_apt("upgrade", "-y")
execute_sudo_apt("autoremove")
execute_sudo_apt("autoclean")

# install necessary apt packages
_apt_packages: Final[tuple[str, ...]] = (
    "git",
    "git-lfs",
    "docker",
    "docker-compose",
    "cockpit",
    "samba",
    "python3-pip",
    "nginx",
    *CUSTOM_CONFIGURATION["additional_apt_packages"],
)
for pkg in _apt_packages:
    execute_sudo_apt_install(pkg)

# refresh snap
execute_sudo_snap("refresh")

# install apt packages
_snap_packages: Final[tuple[str, ...]] = CUSTOM_CONFIGURATION[
    "additional_snap_packages"
]
for pkg in _snap_packages:
    execute_sudo_snap_install(pkg)

# enable Cockpit
check_call(["sudo", "systemctl", "enable", "--now", "cockpit.socket"])

# create folder for samba share
os.makedirs(SHARE_FOLDER_DIR, exist_ok=True)
public_folder(SHARE_FOLDER_DIR)
# add config to smb.conf
add_content("/etc/samba/smb.conf", "[sambashare]")
add_content("/etc/samba/smb.conf", "    comment = Samba on DawnLit")
add_content("/etc/samba/smb.conf", f"    path = {SHARE_FOLDER_DIR}")
add_content("/etc/samba/smb.conf", "    read only = no")
add_content("/etc/samba/smb.conf", "    browsable = yes")
# restart Samba
restart_service("smbd")
# Update the firewall rules to allow Samba traffic
check_call(["sudo", "ufw", "allow", "samba"])
# setup samba user
write_texts(
    "./createSambaUser.sh",
    [
        "#!/bin/bash",
        f'username={CUSTOM_CONFIGURATION["username"]}',
        f'password={CUSTOM_CONFIGURATION["password"]}',
        '(echo "$password"; echo "$password") | smbpasswd -s -a "$username"',
    ],
)
check_call(["sudo", "sh", "./createSambaUser.sh"])

os.remove("./createSambaUser.sh")

# create .config/code-server folder
check_call(["sudo", "mkdir", "-p", "~/.config/code-server"])

# make .config/code-server folder public
public_folder("~/.config/code-server")

# create .local/share/code-server folder
check_call(["sudo", "mkdir", "-p", "~/.local/share/code-server"])

# make .config/code-server folder public
public_folder("~/.local/share/code-server")

# make sure ssl dir exits
os.makedirs("/etc/ssl", exist_ok=True)
# write dns certificate
write_texts("/etc/ssl/cert.pem", CUSTOM_CONFIGURATION["ssl_cert"])
# write dns key
write_texts("/etc/ssl/key.pem", CUSTOM_CONFIGURATION["ssl_key"])

# setup ca
os.makedirs("/etc/ssl/certs", exist_ok=True)
check_call(["sudo", "update-ca-certificates"])
restart_systemctl("docker")

# setup gitlab volumes location
write_texts(".env", [f"GITLAB_HOME={SHARE_FOLDER_DIR}/gitlab", f"GITLAB_SSL=/etc/ssl"])

# reboot system
check_call(["sudo", "reboot"])
