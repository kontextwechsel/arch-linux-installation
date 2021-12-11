# Arch Linux

Arch Linux installation scripts for base system and desktop environment with i3 window manager.

## Color scheme

Generates uniform Monokai color scheme for Sublime Text and xterm. Colors with less standard deviation in Sublime Text theme are converted to gray scale and simliar colors in xterm theme are replaced.

```bash
pacman -Syu python python-numpy
python color_scheme.py
```

## Additional installation steps

### Backlight

```bash
sudo pacman -Syu acpilight
sudo usermod -a -G video "${USER}"

mkdir -p "${HOME}/.local/bin"
tee "${HOME}/.local/bin/backlight" <<EOF
#!/bin/bash

BRIGHTNESS="\$(xbacklight -get)"
while [[ "\${#}" > 0 ]]
    do
        case "\${1}" in
            -i|--increment)
                BRIGHTNESS="\$(("\${BRIGHTNESS}" > 90 ? 100 : "\${BRIGHTNESS}" + 10))"
                shift
                ;;
            -d|--decrement)
                BRIGHTNESS="\$(("\${BRIGHTNESS}" < 10 ? 0 : "\${BRIGHTNESS}" - 10))"
                shift
                ;;
            -r|--reset)
                if [[ -f "\${HOME}/.brightness" ]]
                    then
                        BRIGHTNESS="\$(< "\${HOME}/.brightness")"
                fi
                shift
                ;;
        esac
    done

if [[ "\${BRIGHTNESS}" != "\$(xbacklight -get)" ]]
    then
        xbacklight -set "\${BRIGHTNESS}"
        echo "\${BRIGHTNESS}" > "\${HOME}/.brightness"
        killall -USR1 i3status
fi
EOF
chmod +x "${HOME}/.local/bin/backlight"

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
sudo pacman -Syu tlp
sudo systemctl enable tlp.service

sudo systemctl mask systemd-rfkill.service
sudo systemctl mask systemd-rfkill.socket

sudo tee -a /etc/systemd/logind.conf <<EOF
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
sudo pacman -Syu bluez bluez-utils pulseaudio-bluetooth
sudo systemctl enable bluetooth.service
```

### Hibernate

#### Swap

```bash
sudo dd if=/dev/zero of=/swapfile bs=1K count="$(free -k | awk 'BEGIN { FS=":[[:space:]]*" } $1 == "Mem" { print $2 }' | awk '{ print $1 }')" status=progress
sudo chmod u=rw,go= /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudo tee -a /etc/fstab <<EOF

# /swapfile
/swapfile none swap defaults 0 0
EOF
```

#### Resume

```bash
BUFFER=()
while IFS="=" read -r K V
	do
		IFS=" " read -r -a A <<< "$(sed -r "s/\((.*)\)/\1/g" <<< ${V})"
		if [[ "${K}" = HOOKS ]]
			then
				T=()
				for E in "${A[@]}"
					do
						T+=("${E}")
						if [[ "${E}" = filesystems ]]
							then
								T+=("resume")
						fi
					done
				BUFFER+=("${K}=(${T[*]})")
			else
				BUFFER+=("${K}=(${A[*]})")
		fi
	done < /etc/mkinitcpio.conf
IFS=$'\n'
sudo tee /etc/mkinitcpio.conf <<< "${BUFFER[*]}"
unset IFS
sudo mkinitcpio -p linux

BUFFER=()
while IFS=" " read -r K V
	do
		if [[ "${K}" = options ]]
			then
				IFS=" " read -r -a A <<< "${V}"
				A+=("resume=$(awk '$2 == "/" { print $1 }' /etc/fstab)")
				A+=("resume_offset=$(sudo filefrag -v /swapfile | awk 'BEGIN { FS="[[:space:].:]+" } $2 == "0" { print $5 }')")
				BUFFER+=("${K} ${A[*]}")
			else
				BUFFER+=("${K} ${V}")
		fi
	done < /boot/loader/entries/default.conf
IFS=$'\n'
sudo tee /boot/loader/entries/default.conf <<< "${BUFFER[*]}"
unset IFS
```

#### Battery

```bash
sudo tee /etc/udev/rules.d/90-battery.rules <<EOF
SUBSYSTEM=="power_supply", ATTR{status}=="Discharging", ATTR{capacity}=="[0-5]", RUN+="/usr/bin/systemctl hibernate"
EOF

# Workaround for ACPI not reporting battery status
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

### JetBrains

```bash
tee "${HOME}/.config/i3.d/70-window" <<EOF
for_window [class="jetbrains"] floating disable
for_window [class="jetbrains" title="win"] floating enable
EOF
```

### Scroll wheel

```bash
sudo pacman -Syu imwheel

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

### Sound

Required by _Dell XPS 9310_.

```
sudo pacman -Syu sof-firmware
```

### Touchpad

```bash
sudo tee -a /etc/X11/xorg.conf.d/90-default.conf <<EOF

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

### Video card

#### AMD

```bash
sudo pacman -Syu libva-mesa-driver libva-utils
```

#### Nvidia

```bash
sudo pacman -Syu nvidia

mkdir -p "${HOME}/.config/mpv"
tee "${HOME}/.config/mpv/mpv.conf" <<EOF
hwdec=nvdec
EOF
```

## Docker

```bash
sudo pacman -Syu docker
sudo systemctl enable docker.service
sudo usermod -a -G docker "${USER}"
```

## Dropbear

```bash
sudo pacman -Syu dropbear mkinitcpio-dropbear mkinitcpio-netconf mkinitcpio-utils

sudo cp "${HOME}/.ssh/authorized_keys" /etc/dropbear/root_key
sudo dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key
sudo dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key
sudo dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key

sudo sed -i -r s/"(copy_openssh_keys \|\| generate_keys)"/"#\1"/g /usr/lib/initcpio/install/dropbear
sudo tee /etc/pacman.d/hooks/40-mkinitcpio-dropbear.hook <<-EOF
	[Trigger]
	Type = Package
	Operation = Upgrade
	Target = mkinitcpio-dropbear

	[Action]
	When = PostTransaction
	Exec = /usr/bin/sed -i -r s/"(copy_openssh_keys \|\| generate_keys)"/"#\1"/g /usr/lib/initcpio/install/dropbear
EOF

BUFFER=()
while IFS="=" read -r K V
	do
		IFS=" " read -r -a A <<< "$(sed -r "s/\((.*)\)/\1/g" <<< "${V}")"
		if [[ "${K}" = HOOKS ]]
			then
				T=()
				for E in "${A[@]}"
					do
						if [[ "${E}" = encrypt ]]
							then
								T+=("netconf")
								T+=("dropbear")
								T+=("encryptssh")
							else
								T+=("${E}")
						fi
					done
				BUFFER+=("${K}=(${T[*]})")
			else
				BUFFER+=("${K}=(${A[*]})")
		fi
	done < /etc/mkinitcpio.conf
IFS=$'\n'
sudo tee /etc/mkinitcpio.conf <<< "${BUFFER[*]}"
unset IFS
sudo mkinitcpio -p linux

NIC="$(ip --brief link show | awk '$2 == "UP" { print $1; exit }')"
KERNEL_NIC="$(sudo dmesg | grep -oP "(?<=${NIC}: renamed from )(.+)(?=$)")"
if [[ -n "${KERNEL_NIC}:+SUBSTITUTION" ]]
	then
		NIC="${KERNEL_NIC}"
fi

BUFFER=()
while IFS=" " read -r K V
	do
		if [[ "${K}" = options ]]
			then
				IFS=" " read -r -a A <<< "${V}"
				A+=("ip=:::::${NIC}:dhcp")
				BUFFER+=("${K} ${A[*]}")
			else
				BUFFER+=("${K} ${V}")
		fi
	done < /boot/loader/entries/default.conf
IFS=$'\n'
sudo tee /boot/loader/entries/default.conf <<< "${BUFFER[*]}"
unset IFS
```

## Flatpak

```bash
PACKAGES=(
    flatpak
    xdg-desktop-portal
    xdg-desktop-portal-gtk
)
sudo pacman -Syu "${PACKAGES[@]}"

sed -i "1s/^/dbus-update-activation-environment --systemd DBUS_SESSION_BUS_ADDRESS DISPLAY XAUTHORITY\n/g" "${HOME}/.xinitrc"

flatpak remote-add --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
```

## libvirt

```bash
PACKAGES=(
	dnsmasq
	ebtables
	edk2-ovmf
	libvirt
	openbsd-netcat
	qemu
	virt-manager
)
sudo pacman -Syu "${PACKAGES[@]}"
sudo systemctl enable libvirtd.service
sudo usermod -a -G libvirt "${USER}"

echo "virt-manager=/usr/bin/virt-manager" >> "${HOME}/.config/application-launcher/config"
```
