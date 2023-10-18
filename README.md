# Arch Linux

Arch Linux installation scripts for base system and desktop environment with i3 window manager.

1. Boot Arch ISO (https://archlinux.org/download/) and connect to network.
2. Execute `arch-linux-installation` to install base system and reboot.
3. Execute `arch-linux-desktop-installation` to install desktop environment and reboot.
4. Press **Super** + **Enter** to open new terminal.

## Applications

Applications in **dmenu** can be maintained with `application-launcher`:

`Usage: application-launcher [--add|--remove|--list] [APPLICATION] [EXECUTABLE] [ARGUMENTS...]`

## Color scheme

Generates uniform Monokai color scheme for Sublime Text and xterm. Colors with less standard deviation in Sublime Text theme are converted to gray scale and simliar colors in xterm theme are replaced.

```bash
pacman --sync --refresh python python-numpy python-requests
python color_scheme.py
```

## Secure Boot

1. Delete all keys in UEFI.
2. Execute `secure-boot-installation`.
2. Enable Secure Boot in UEFI.

Microsoft UEFI signature may be required for dedicated graphics cards. Microsoft Production signature is required for booting Windows.

### Secure Boot status

Prints Secure Boot status before password prompt for disk encryption.

```bash
sudo tee /etc/initcpio/install/secure-boot-status << EOF
#!/bin/bash

build() {
  add_binary "/usr/bin/awk"
  add_binary "/usr/bin/od"
  add_runscript
}

help() {
  :
}
EOF

sudo tee /etc/initcpio/hooks/secure-boot-status << EOF
#!/usr/bin/ash

run_hook () {
  if [ -d /sys/firmware/efi/efivars/ ]; then
    if [ "\$(od --address-radix=n --format=u1 /sys/firmware/efi/efivars/SecureBoot-????????-????-????-????-???????????? | awk '{ print \$NF }')" -eq 1 ]; then
      readonly status="\e[32menabled\e[0m"
    else
      readonly status="\e[31mdisabled\e[0m"
    fi
    printf "Secure Boot is %b\n\n" "\${status}"
  fi
}
EOF

buffer=()
while IFS="=" read -r key value; do
  IFS=" " read -r -a variables <<< "$(sed -r "s/\((.*)\)/\1/g" <<< "${value}")"
  if [[ "${key}" == "HOOKS" ]]; then
    hooks=()
    for hook in "${variables[@]}"; do
      if [[ "${hook}" != "secure-boot-status" ]]; then
        if [[ "${hook}" == "encrypt" ]]; then
          hooks+=("secure-boot-status")
        fi
        hooks+=("${hook}")
      fi
    done
    buffer+=("${key}=(${hooks[*]})")
  else
    buffer+=("${key}=(${variables[*]})")
  fi
done < /etc/mkinitcpio.conf
printf "%s\n" "${buffer[@]}" | sudo tee /etc/mkinitcpio.conf

sudo mkinitcpio -p linux
```

## Additional installation steps

### Backlight

```bash
sudo pacman --sync --refresh acpilight
sudo usermod --append --groups video "${USER}"

mkdir --parents "${HOME}/.local/bin/"
mkdir --parents "${HOME}/.local/share/bash-completion/completions/"
tee "${HOME}/.local/bin/backlight" << EOF
#!/bin/bash

readonly brightness="\$(xbacklight -get)"

function set_brightness() {
  xbacklight -set "\$1"
  printf "%s\n" "\$1" > "\${HOME}/.brightness"
  killall -USR1 i3status
}

if [[ "\$#" -eq 1 ]]; then
  case "\$1" in
    -i | --increment)
      set_brightness "\$(( "\${brightness}" > 90 ? 100 : "\${brightness}" + 10 ))"
      exit
      ;;
    -d | --decrement)
      set_brightness "\$(( "\${brightness}" < 10 ? 0 : "\${brightness}" - 10 ))"
      exit
      ;;
    -r | --reset)
      set -x
      if [[ -f "\${HOME}/.brightness" ]]; then
        value="\$(< "\${HOME}/.brightness")"
      else
        value="\${brightness}"
      fi
      if [[ "\${value}" =~ ^([1-9]?[0-9]|100)\$ ]]; then
        set_brightness "\${value}"
      else
        set_brightness "\${brightness}"
      fi
      set +x
      exit
      ;;
  esac
fi

printf "Usage: backlight [--increment|--decrement|--reset]\n"
exit 1
EOF
tee "${HOME}/.local/share/bash-completion/completions/backlight" << EOF
function _backlight() {
  if [[ "${COMP_CWORD}" -eq 1 ]]; then
    readarray -t COMPREPLY < <(compgen -W "--increment --decrement --reset" -- "\${COMP_WORDS[\${COMP_CWORD}]}")
  fi
}
complete -F _backlight backlight
EOF
chmod +x "${HOME}/.local/bin/backlight"

tee "${HOME}/.brightness" << EOF
"$(xbacklight -get)"
EOF

tee "${HOME}/.config/i3.d/41-backlight" << EOF
bindsym XF86MonBrightnessUp exec --no-startup-id backlight --increment
bindsym XF86MonBrightnessDown exec --no-startup-id backlight --decrement
exec --no-startup-id backlight --reset
EOF

tee "${HOME}/.config/i3status.d/35-brightness" << EOF
order += "read_file brightness"
read_file brightness {
    path = "\${HOME}/.brightness"
    format = "🔆 %content%"
}
EOF

sudo systemctl mask systemd-backlight@.service
```

### Banner

```bash
sudo tee /etc/initcpio/banner << EOF
                __                                 _                 _
    /\         / _|                           /\  | |               | |
   /  \  _   _| |_   _____   _ _ __ ___      /  \ | |_ ___ _ __ ___ | |
  / /\ \| | | |  _| |_  / | | | '_ \` _ \    / /\ \| __/ _ \ '_ \` _ \| |
 / ____ \ |_| | |    / /| |_| | | | | | |  / ____ \ ||  __/ | | | | |_|
/_/    \_\__,_|_|   /___|\__,_|_| |_| |_| /_/    \_\__\___|_| |_| |_(_)

EOF

sudo tee /etc/initcpio/install/banner << EOF
#!/bin/bash

build() {
  if [[ -s /etc/initcpio/banner ]]; then
    add_file "/etc/initcpio/banner"
    add_runscript
  fi
}

help() {
  :
}
EOF

sudo tee /etc/initcpio/hooks/banner << EOF
#!/usr/bin/ash

run_hook() {
  cat /etc/initcpio/banner
}
EOF

buffer=()
while IFS="=" read -r key value; do
  IFS=" " read -r -a variables <<< "$(sed -r "s/\((.*)\)/\1/g" <<< "${value}")"
  if [[ "${key}" == "HOOKS" ]]; then
    hooks=()
    for hook in "${variables[@]}"; do
      if [[ "${hook}" != "banner" ]]; then
        hooks+=("${hook}")
        if [[ "${hook}" == "base" ]]; then
          hooks+=("banner")
        fi
      fi
    done
    buffer+=("${key}=(${hooks[*]})")
  else
    buffer+=("${key}=(${variables[*]})")
  fi
done < /etc/mkinitcpio.conf
printf "%s\n" "${buffer[@]}" | sudo tee /etc/mkinitcpio.conf

sudo mkinitcpio -p linux
```

### Battery

```bash
sudo pacman --sync --refresh tlp
sudo systemctl enable tlp.service

sudo systemctl mask systemd-rfkill.service
sudo systemctl mask systemd-rfkill.socket

sudo tee --append /etc/systemd/logind.conf << EOF
HandleLidSwitch=suspend
HandleLidSwitchDocked=suspend
EOF

tee "${HOME}/.config/i3status.d/40-battery" << EOF
order += "battery 0"
battery 0 {
    path = "/sys/class/power_supply/BAT%d/uevent"
    format = "%status %percentage"
    format_down = ""
    status_unk = "?"
    status_bat = "🔋"
    status_chr = "⚡"
    status_full = "🔌"
    low_threshold = 10
    last_full_capacity = true
    integer_battery_capacity = true
}
EOF
```

### Bluetooth

```bash
sudo pacman --sync --refresh bluez bluez-utils
sudo systemctl enable bluetooth.service
```

### Hibernate

Requires UEFI mode!

#### Swap

```bash
sudo dd if=/dev/zero of=/swapfile bs=1K count="$(free -k | awk '$1 == "Mem:" { print $2 }')" status=progress
sudo chmod u=rw,go= /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudo tee --append /etc/fstab << EOF

# /swapfile
/swapfile none swap defaults 0 0
EOF
```

#### Resume

```bash
swap_partition_id="$(lsblk -n -o MOUNTPOINT,UUID | awk '$1 == "/" { print $2 }')"
swap_file_offset="$(sudo filefrag -v /swapfile | awk '$1 == "0:" { match($4, /[0-9]+/, m); print m[0] }')"
sudo tee /etc/cmdline.d/hibernate.conf << EOF
resume=UUID=${swap_partition_id} resume_offset=${swap_file_offset}
EOF

buffer=()
while IFS="=" read -r key value; do
  IFS=" " read -r -a variables <<< "$(sed -r "s/\((.*)\)/\1/g" <<< ${value})"
  if [[ "${key}" == "HOOKS" ]]; then
    hooks=()
    for hook in "${variables[@]}"; do
      if [[ "${hook}" != "resume" ]]; then
        hooks+=("${hook}")
        if [[ "${hook}" == "filesystems" ]]; then
          hooks+=("resume")
        fi
      fi
    done
    buffer+=("${key}=(${hooks[*]})")
  else
    buffer+=("${key}=(${variables[*]})")
  fi
done < /etc/mkinitcpio.conf
printf "%s\n" "${buffer[@]}" | sudo tee /etc/mkinitcpio.conf

sudo mkinitcpio --preset linux
```

#### Battery

```bash
sudo tee /etc/udev/rules.d/90-battery.rules << EOF
SUBSYSTEM=="power_supply", ATTR{status}=="Discharging", ATTR{capacity}=="[0-5]", RUN+="/usr/bin/systemctl hibernate"
EOF
```

### Touchpad

```bash
sudo tee --append /etc/X11/xorg.conf.d/90-default.conf << EOF

Section "InputClass"
        Identifier "Touchpad control"
        MatchIsTouchpad "on"
        Driver "libinput"
        Option "ClickMethod" "clickfinger"
        Option "NoTapping"
        Option "ScrollMethod" "twofinger"
        Option "NaturalScrolling"
EndSection
EOF
```

### Virtualization

#### Docker

```bash
sudo pacman --sync --refresh docker docker-buildx docker-compose
sudo systemctl enable docker.service
sudo usermod --append --groups docker "${USER}"
```

#### KVM/QEMU

```bash
packages=(
  dnsmasq
  libvirt
  openbsd-netcat
  qemu-desktop
  virt-manager
)
sudo pacman --sync --refresh "${packages[@]}"
sudo systemctl enable libvirtd.service
sudo usermod --append --groups libvirt "${USER}"

application-launcher --add "virt-manager" "/usr/bin/virt-manager"
```
