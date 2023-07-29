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

## Additional installation steps

### Backlight

```bash
sudo pacman --sync --refresh acpilight
sudo usermod --append --groups video "${USER}"

mkdir --parents "${HOME}/.local/bin/"
mkdir --parents "${HOME}/.local/share/bash-completion/completions/"
tee "${HOME}/.local/bin/backlight" <<EOF
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
      set_brightness "\$(("\${brightness}" > 90 ? 100 : "\${brightness}" + 10))"
      exit
      ;;
    -d | --decrement)
      set_brightness "\$(("\${brightness}" < 10 ? 0 : "\${brightness}" - 10))"
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
tee "${HOME}/.local/share/bash-completion/completions/backlight" <<EOF
function _backlight() {
  if [[ "${COMP_CWORD}" -eq 1 ]]; then
    readarray -t COMPREPLY < <(compgen -W "--increment --decrement --reset" -- "\${COMP_WORDS[\${COMP_CWORD}]}")
  fi
}
complete -F _backlight backlight
EOF
chmod +x "${HOME}/.local/bin/backlight"

tee "${HOME}/.brightness" <<EOF
"$(xbacklight -get)"
EOF

tee "${HOME}/.config/i3.d/41-backlight" <<EOF
bindsym XF86MonBrightnessUp exec --no-startup-id backlight --increment
bindsym XF86MonBrightnessDown exec --no-startup-id backlight --decrement
exec --no-startup-id backlight --reset
EOF

tee "${HOME}/.config/i3status.d/35-brightness" <<EOF
order += "read_file brightness"
read_file brightness {
    path = "\${HOME}/.brightness"
    format = "🔆 %content%"
}
EOF

sudo systemctl mask systemd-backlight@.service
```

### Battery

```bash
sudo pacman --sync --refresh tlp
sudo systemctl enable tlp.service

sudo systemctl mask systemd-rfkill.service
sudo systemctl mask systemd-rfkill.socket

sudo tee --append /etc/systemd/logind.conf <<EOF
HandleLidSwitch=suspend
HandleLidSwitchDocked=suspend
EOF

tee "${HOME}/.config/i3status.d/40-battery" <<EOF
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

#### Swap

```bash
sudo dd if=/dev/zero of=/swapfile bs=1K count="$(free -k | awk '$1 == "Mem:" { print $2 }')" status=progress
sudo chmod u=rw,go= /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudo tee --append /etc/fstab <<EOF

# /swapfile
/swapfile none swap defaults 0 0
EOF
```

#### Resume

```bash
buffer=()
while IFS="=" read -r key value; do
  IFS=" " read -r -a array <<< "$(sed -r "s/\((.*)\)/\1/g" <<< ${value})"
  if [[ "${key}" = "HOOKS" ]]; then
    hooks=()
    for hook in "${array[@]}"; do
      hooks+=("${hook}")
      if [[ "${hook}" = "filesystems" ]]; then
        hooks+=("resume")
      fi
    done
    buffer+=("${key}=(${hooks[*]})")
  else
    buffer+=("${key}=(${array[*]})")
  fi
done < /etc/mkinitcpio.conf
printf "%s\n" "${buffer[@]}" | sudo tee /etc/mkinitcpio.conf
sudo mkinitcpio --preset linux

buffer=()
while IFS=" " read -r key value; do
  if [[ "${key}" = "options" ]]; then
    IFS=" " read -r -a array <<< "${value}"
    array+=("resume=$(awk '$2 == "/" { print $1 }' /etc/fstab)")
    array+=("resume_offset=$(sudo filefrag -v /swapfile | awk 'BEGIN { FS="[[:space:].:]+" } $2 == "0" { print $5 }')")
    buffer+=("${key} ${array[*]}")
  else
    buffer+=("${key} ${value}")
  fi
done < /boot/loader/entries/default.conf
printf "%s\n" "${buffer[@]}" | sudo tee /boot/loader/entries/default.conf
```

#### Battery

```bash
sudo tee /etc/udev/rules.d/90-battery.rules <<EOF
SUBSYSTEM=="power_supply", ATTR{status}=="Discharging", ATTR{capacity}=="[0-5]", RUN+="/usr/bin/systemctl hibernate"
EOF
```

##### Workaround for ACPI not reporting battery status

```bash
sudo tee /usr/lib/systemd/system/power-trigger.service <<EOF
[Unit]
Description=Power Trigger

[Service]
Type=oneshot
ExecStart=udevadm trigger --subsystem-match=power_supply --action=change --attr-match=status=Discharging

[Install]
WantedBy=default.target
EOF
sudo tee /usr/lib/systemd/system/power-trigger.timer <<EOF
[Unit]
Description=Power Trigger

[Timer]
OnCalendar=*:0/1
Unit=power-trigger.service

[Install]
WantedBy=default.target
EOF
sudo systemctl enable power-trigger.timer
```

### Scroll wheel

```bash
sudo pacman --sync --refresh imwheel

tee "${HOME}/.imwheelrc" <<EOF
".*"
None, Up, Button4, 3
None, Down, Button5, 3
Control_L, Up, Control_L|Button4
Control_L, Down, Control_L|Button5
Shift_L, Up, Shift_L|Button4
Shift_L, Down, Shift_L|Button5
EOF

tee "${HOME}/.config/i3.d/65-imwheel" <<EOF
exec --no-startup-id imwheel -b 45
EOF
```

### Touchpad

```bash
sudo tee --append /etc/X11/xorg.conf.d/90-default.conf <<EOF

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

## Dropbear

```bash
sudo pacman --sync --refresh dropbear mkinitcpio-dropbear mkinitcpio-netconf mkinitcpio-utils

sudo cp "${HOME}/.ssh/authorized_keys" /etc/dropbear/root_key
sudo dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key
# Suppress missing key errors
sudo ln -s dropbear_ed25519_host_key /etc/dropbear/dropbear_dss_host_key
sudo ln -s dropbear_ed25519_host_key /etc/dropbear/dropbear_ecdsa_host_key
sudo ln -s dropbear_ed25519_host_key /etc/dropbear/dropbear_rsa_host_key

sudo sed --in-place -E "s/(copy_openssh_keys \|\| generate_keys)/#\1/g" /usr/lib/initcpio/install/dropbear
sudo tee /etc/pacman.d/hooks/40-mkinitcpio-dropbear.hook <<EOF
[Trigger]
Type = Package
Operation = Upgrade
Target = mkinitcpio-dropbear

[Action]
When = PostTransaction
Exec = /usr/bin/sed --in-place -E "s/(copy_openssh_keys \|\| generate_keys)/#\1/g" /usr/lib/initcpio/install/dropbear
EOF

buffer=()
while IFS="=" read -r key value; do
  IFS=" " read -r -a array <<< "$(sed -r "s/\((.*)\)/\1/g" <<< "${value}")"
  if [[ "${key}" = "HOOKS" ]]; then
    hooks=()
    for hook in "${array[@]}"; do
      if [[ "${hook}" = "encrypt" ]]; then
        hooks+=("netconf")
        hooks+=("dropbear")
        hooks+=("encryptssh")
      else
        hooks+=("${hook}")
      fi
    done
    buffer+=("${key}=(${hooks[*]})")
  else
    buffer+=("${key}=(${array[*]})")
  fi
done < /etc/mkinitcpio.conf
printf "%s\n" "${buffer[@]}" | sudo tee /etc/mkinitcpio.conf

network_interface="$(ip -brief link show | awk '$2 == "UP" { print $1; exit }')"
kernel_network_interface="$(sudo dmesg | grep -oP "(?<=${network_interface}: renamed from )(.+)(?=$)")"
if [[ -n "${kernel_network_interface}:+substitution" ]]; then
  network_interface="${kernel_network_interface}"
fi

if [[ -f /boot/loader/entries/default.conf ]]; then
  buffer=()
  while IFS=" " read -r key value; do
    if [[ "${key}" = "options" ]]; then
      IFS=" " read -r -a options <<< "${value}"
      options+=("ip=:::::${network_interface}:dhcp")
      buffer+=("${key} ${options[*]}")
    else
      buffer+=("${key} ${value}")
    fi
  done < /boot/loader/entries/default.conf
  printf "%s\n" "${buffer[@]}" | sudo tee /boot/loader/entries/default.conf
fi

if [[ -f /etc/kernel/cmdline ]]; then
  IFS=" " read -r -a options < /etc/kernel/cmdline
  options+=("ip=:::::${network_interface}:dhcp")
  printf "%s\n" "${options[*]}" | sudo tee /etc/kernel/cmdline
fi

sudo mkinitcpio --preset linux
if [[ -d /etc/secure-boot/ ]]; then
  sudo sbsign --cert /etc/secure-boot/db.crt --key /etc/secure-boot/db.key --output /boot/EFI/Linux/arch-linux.efi /boot/EFI/Linux/arch-linux.efi
fi
```

## Virtualization

### Docker

```bash
sudo pacman --sync --refresh docker docker-compose
sudo systemctl enable docker.service
sudo usermod --append --groups docker "${USER}"
```

### KVM/QEMU

```bash
PACKAGES=(
  dnsmasq
  libvirt
  openbsd-netcat
  qemu
  virt-manager
)
sudo pacman --sync --refresh "${PACKAGES[@]}"
sudo systemctl enable libvirtd.service
sudo usermod --append --groups libvirt "${USER}"

application-launcher --add "virt-manager" "/usr/bin/virt-manager"
```
