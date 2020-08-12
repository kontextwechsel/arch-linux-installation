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
tee "${HOME}/.local/bin/xbacklight" <<-EOF
	#!/bin/sh

	/usr/bin/xbacklight "\$@"
	/usr/bin/xbacklight -get > "\${HOME}/.brightness"
	killall -USR1 i3status
EOF

tee "${HOME}/.i3/config.d/41-backlight" <<-EOF
	bindsym XF86MonBrightnessUp exec --no-startup-id xbacklight -inc 10
	bindsym XF86MonBrightnessDown exec --no-startup-id xbacklight -dec 10
	exec --no-startup-id xbacklight -set 10
EOF

tee "${HOME}/.i3/status.d/35-brightness" <<-EOF
	order += "read_file brightness"
	read_file brightness {
	    path = "\${HOME}/.brightness"
	    format = "🔆 %content%"
	}
EOF
```

### Battery

```bash
sudo pacman -Syu tlp
sudo systemctl enable tlp.service

sudo tee -a /etc/systemd/logind.conf <<-EOF
	HandleLidSwitch=suspend
	HandleLidSwitchDocked=suspend
EOF

tee "${HOME}/.i3/status.d/40-battery" <<-EOF
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
sudo pacman -Syu blueman libappindicator-gtk3
sudo systemctl enable bluetooth.service

tee "${HOME}/.i3/config.d/64-blueman" <<-EOF
	exec --no-startup-id blueman-applet
EOF
```

### Touchpad

```bash
sudo tee -a /etc/X11/xorg.conf.d/90-default.conf <<-EOF

	Section "InputClass"
	    Identifier "Touchpad control"
	    MatchIsTouchpad "on"
	    Driver "libinput"
	        Option "ClickMethod" "clickfinger"
	        Option "Tapping" "off"
	        Option "ScrollMethod" "twofinger"
	        Option "NaturalScrolling" "on"
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
tee "${HOME}/.config/mpv/mpv.conf" <<-EOF
	hwdec=nvdec
EOF
```

### Window

```bash
tee "${HOME}/.i3/config.d/70-window" <<-EOF
	for_window [class="jetbrains"] floating disable
	for_window [class="jetbrains" title="win"] floating enable
EOF
```

## Dropbear

```bash
sudo pacman -Syu mkinitcpio-dropbear mkinitcpio-netconf mkinitcpio-utils

sudo cp "${HOME}/.ssh/authorized_keys" /etc/dropbear/root_key
sudo dropbearkey -t rsa -f /etc/dropbear/dropbear_rsa_host_key
sudo dropbearkey -t ecdsa -f /etc/dropbear/dropbear_ecdsa_host_key
sudo dropbearkey -t ed25519 -f /etc/dropbear/dropbear_ed25519_host_key
sudo sed -i -r s/"(copy_openssh_keys \|\| generate_keys)"/"#\1"/g /usr/lib/initcpio/install/dropbear

sudo sed -i s/"BINARIES=()"/"BINARIES=(\/usr\/lib\/libgcc_s.so.1)"/g /etc/mkinitcpio.conf
sudo sed -i s/"HOOKS=(base udev autodetect modconf block keyboard keymap encrypt filesystems fsck)"/"HOOKS=(base udev autodetect modconf block keyboard keymap netconf dropbear encryptssh filesystems fsck)"/g /etc/mkinitcpio.conf
sudo mkinitcpio -p linux

NIC="$(grep -oP "(?<=Name=).*" $(find /etc/systemd/network -type f | sort | head -1))"
sudo sed -i -r s/"GRUB_CMDLINE_LINUX=\"(.*)\""/"GRUB_CMDLINE_LINUX=\"\1 ip=:::::${NIC}:dhcp\""/g /etc/default/grub
sudo grub-mkconfig -o /boot/grub/grub.cfg
```

## libvirt

```bash
PACKAGES=(
	dnsmasq
	ebtables
	libvirt
	openbsd-netcat
	qemu
	virt-manager
)
sudo pacman -Syu ${PACKAGES[*]}

sudo systemctl enable libvirtd.service
sudo usermod -a -G libvirt "${USER}"
```
