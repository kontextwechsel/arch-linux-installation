# Arch Linux

Arch Linux installation scripts for base system and desktop environment with i3 window manager.

1. Boot Arch ISO (https://archlinux.org/download/) and connect to network.
2. Execute `arch-linux-installation` to install base system and reboot.
3. Execute `arch-linux-desktop-installation` to install desktop environment and reboot.
4. Press **Super** + **Enter** to open new terminal.

## Applications

Applications in `dmenu` can be maintained with `application-launcher`:

`Usage: application-launcher [--add|--remove|--list] [APPLICATION] [EXECUTABLE] [ARGUMENTS...]`

## Color scheme

Generates uniform Monokai color scheme for Sublime Text and xterm. Colors with less standard deviation in Sublime Text theme are converted to gray scale and simliar colors in xterm theme are replaced.

```bash
pacman --sync --refresh python python-numpy python-requests python-yaml
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
sudo tee /etc/initcpio/install/secure-boot-status <<- EOF
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

sudo tee /etc/initcpio/hooks/secure-boot-status <<- EOF
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
        hooks+=("${hook}")
        if [[ "${hook}" == "base" ]]; then
          hooks+=("secure-boot-status")
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

## Additional installation steps

### Backlight

```bash
sudo pacman --sync --refresh brightnessctl
sudo usermod --append --groups video "${USER}"

sudo tee /usr/local/bin/backlight <<- EOF
	#!/bin/bash

	if [[ -n "\${DISPLAY}" ]]; then
	  readonly brightness="\$(( "\$(brightnessctl get)" / ("\$(brightnessctl max)" / 100) ))"

	  function set() {
	    brightnessctl --quiet set "\$1%"
	    printf "%s\n" "\$1" > "\${HOME}/.brightness"
	    killall -USR1 i3status
	  }

	  function reset() {
	    if [[ ! -f "\${HOME}/.brightness" ]]; then
	      return 1
	    fi
	    local value="\$(< "\${HOME}/.brightness")"
	    if [[ ! "\${value}" =~ ^([1-9]?[0-9]|100)\$ ]]; then
	      return 1
	    fi
	    set "\${value}"
	  }

	  case "\$1" in
	    -i | --increment)
	      set "\$(( "\${brightness}" > 90 ? 100 : "\${brightness}" + 10 ))"
	      ;;
	    -d | --decrement)
	      set "\$(( "\${brightness}" < 10 ? 0 : "\${brightness}" - 10 ))"
	      ;;
	    -r | --reset)
	      if ! reset; then
	        set "\${brightness}"
	      fi
	      ;;
	    *)
	      printf "Usage: %s [--increment|--decrement|--reset]\n" "\$(basename \${BASH_SOURCE[0]})"
	      exit 1
	      ;;
	  esac
	fi
EOF

sudo chmod +x /usr/local/bin/backlight

sudo tee /usr/local/share/bash-completion/completions/backlight <<- EOF
	function _backlight() {
	  if [[ "\${COMP_CWORD}" -eq 1 ]]; then
	    readarray -t COMPREPLY < <(compgen -W "--increment --decrement --reset" -- "\${COMP_WORDS["\${COMP_CWORD}"]}")
	  fi
	}
	complete -F _backlight backlight
EOF

tee "${HOME}/.brightness" <<- EOF
	$(( "$(brightnessctl get)" / ("$(brightnessctl max)" / 100) ))
EOF

sudo tee /etc/skel/.config/i3.d/41-backlight <<- EOF
	bindsym XF86MonBrightnessUp exec --no-startup-id backlight --increment
	bindsym XF86MonBrightnessDown exec --no-startup-id backlight --decrement
	exec --no-startup-id backlight --reset
EOF
cp /etc/skel/.config/i3.d/41-backlight "${HOME}/.config/i3.d/"

sudo tee /etc/skel/.config/i3status.d/35-brightness <<- EOF
	order += "read_file brightness"
	read_file brightness {
	    path = "\${HOME}/.brightness"
	    format = "🔆 %content%"
	}
EOF
cp /etc/skel/.config/i3status.d/35-brightness "${HOME}/.config/i3status.d/"
```

### Banner

```bash
sudo tee /etc/initcpio/banner <<- EOF
	                __                                 _                 _
	    /\         / _|                           /\  | |               | |
	   /  \  _   _| |_   _____   _ _ __ ___      /  \ | |_ ___ _ __ ___ | |
	  / /\ \| | | |  _| |_  / | | | '_ \` _ \    / /\ \| __/ _ \ '_ \` _ \| |
	 / ____ \ |_| | |    / /| |_| | | | | | |  / ____ \ ||  __/ | | | | |_|
	/_/    \_\__,_|_|   /___|\__,_|_| |_| |_| /_/    \_\__\___|_| |_| |_(_)
EOF

sudo tee /etc/initcpio/install/banner <<- EOF
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

sudo tee /etc/initcpio/hooks/banner <<- EOF
	#!/usr/bin/ash

	run_hook() {
	  banner="\$(cat /etc/initcpio/banner)"
	  printf "%s\n\n" "\${banner}"
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

sudo mkinitcpio --preset linux
```

### Battery

```bash
sudo pacman --sync --refresh tlp
sudo systemctl enable tlp.service

sudo systemctl mask systemd-rfkill.service systemd-rfkill.socket

sudo tee --append /etc/systemd/logind.conf <<- EOF
	HandleLidSwitch=suspend
	HandleLidSwitchDocked=suspend
EOF

sudo tee /etc/skel/.config/i3status.d/40-battery <<- EOF
	order += "battery 0"
	battery 0 {
	    path = "/sys/class/power_supply/BAT%d/uevent"
	    format = "%status %percentage"
	    format_down = ""
	    status_unk = "?"
	    status_idle = "-"
	    status_bat = "🔋"
	    status_chr = "⚡"
	    status_full = "🔌"
	    low_threshold = 10
	    last_full_capacity = true
	    integer_battery_capacity = true
	}
EOF
cp /etc/skel/.config/i3status.d/40-battery "${HOME}/.config/i3status.d/"
```

### Bluetooth

```bash
sudo pacman --sync --refresh bluez bluez-utils
sudo systemctl enable bluetooth.service
```

### Hibernate

Requires UEFI and disabled kernel lockdown mode!

#### Swap

```bash
sudo dd if=/dev/zero of=/swapfile bs=1K count="$(free -k | awk '$1 == "Mem:" { print $2 }')" status=progress
sudo chmod u=rw,go= /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
sudo tee --append /etc/fstab <<- EOF

	# /swapfile
	/swapfile none swap defaults 0 0
EOF
```

#### Resume

```bash
swap_partition_id="$(lsblk --noheadings --list --output MOUNTPOINT,UUID | awk '$1 == "/" { print $2 }')"
swap_file_offset="$(sudo filefrag -v /swapfile | awk '$1 == "0:" { match($4, /[0-9]+/, m); print m[0] }')"
sudo tee /etc/cmdline.d/hibernate.conf <<- EOF
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

sudo rm /etc/cmdline.d/security.conf

sudo mkinitcpio --preset linux
```

#### Battery

```bash
sudo tee /etc/udev/rules.d/90-battery.rules <<- EOF
	SUBSYSTEM=="power_supply", ATTR{status}=="Discharging", ATTR{capacity}=="[0-5]", RUN+="/usr/bin/systemctl hibernate"
EOF
```

### Sublime Text

```bash
readonly sublime_text_key_id="1EDDE2CDFC025D17F6DA9EC0ADAE6AD28A8F901A"
sudo pacman-key --recv-keys "${sublime_text_key_id}"
sudo pacman-key --lsign-key "${sublime_text_key_id}"
sudo tee /etc/pacman.d/conf/sublime-text <<- EOF
	[sublime-text]
	Server = https://download.sublimetext.com/arch/stable/x86_64
EOF

sudo pacman --sync --refresh sublime-text

application-launcher --add sublime-text /usr/bin/subl --new-window

sudo mkdir --parents /etc/skel/.config/sublime-text/Packages/User/
unzip -p "/opt/sublime_text/Packages/Color Scheme - Default.sublime-package" Monokai.sublime-color-scheme \
  | sed -E ':a;N;$!ba;s/,(\s*)(}|])/\1\2/g' \
  | jq '.name = "Auf zum Atem!"' \
  | jq '.author = "Me"' \
  | jq '.variables.black = "#000000"' \
  | jq '.variables.black2 = "#202020"' \
  | jq '.variables.black3 = "#282828"' \
  | jq '.variables.blue = "#67d8ef"' \
  | jq '.variables.grey = "#535353b3"' \
  | jq '.variables.orange = "#fd9621"' \
  | jq '.variables.orange2 = "#9f570f"' \
  | jq '.variables.orange3 = "#ffe894"' \
  | jq '.variables.purple = "#ac80ff"' \
  | jq '.variables.red = "#f83535"' \
  | jq '.variables.red2 = "#f92472"' \
  | jq '.variables.white = "#f7f7f7"' \
  | jq '.variables.white2 = "#f7f7f7"' \
  | jq '.variables.white3 = "#f7f7f7"' \
  | jq '.variables.yellow = "#ffe894"' \
  | jq '.variables.yellow2 = "#a6e22c"' \
  | jq '.variables.yellow3 = "#cecece"' \
  | jq '.variables.yellow4 = "#3c3c3c"' \
  | jq '.variables.yellow5 = "#6f6f6f"' \
  | sudo tee "/etc/skel/.config/sublime-text/Packages/User/Auf zum Atem"'!'".sublime-color-scheme"
sudo tee /etc/skel/.config/sublime-text/Packages/User/Preferences.sublime-settings <<- EOF
	{
	    "always_prompt_for_file_reload": true,
	    "close_windows_when_empty": true,
	    "color_scheme": "Packages/User/Auf zum Atem!.sublime-color-scheme",
	    "drag_text": false,
	    "draw_white_space": [ "all" ],
	    "ensure_newline_at_eof_on_save": true,
	    "fallback_encoding": "ISO 8859-1",
	    "font_face": "Source Code Pro",
	    "font_size": 14,
	    "hardware_acceleration": "opengl", // Requires OpenGL support!
	    "highlight_line": true,
	    "highlight_modified_tabs": true,
	    "hot_exit": "disabled",
	    "line_padding_bottom": 3,
	    "line_padding_top": 3,
	    "open_files_in_new_window": "always",
	    "remember_workspace": false,
	    "ruler_style": "stippled",
	    "rulers": [ 80 ],
	    "scroll_speed": 0,
	    "selection_description_column_type": "real",
	    "show_encoding": true,
	    "show_line_endings": true,
	    "trim_trailing_white_space_on_save": "all",
	    "update_check": false, // Requires Sublime Text license!
	}
EOF
sudo tee "/etc/skel/.config/sublime-text/Packages/User/Default (Linux).sublime-keymap" <<- EOF
	[]
EOF
sudo mkdir --parents /etc/skel/.config/sublime-text/Local/
sudo tee /etc/skel/.config/sublime-text/Local/Session.sublime_session <<- EOF
	{"windows":[{"menu_visible":false}]}
EOF

rsync --recursive --links --verbose /etc/skel/.config/sublime-text/ "${HOME}/.config/sublime-text/"

readonly -a types=(
  application/javascript
  application/json
  application/sql
  application/xml
  application/x-shellscript
  text/css
  text/csv
  text/html
  text/markdown
  text/plain
  text/x-c
  text/x-c++
  text/x-java
  text/x-python
)
for type in "${types[@]}"; do
  xdg-mime default sublime_text.desktop "${type}"
done
```

### Touchpad

```bash
sudo tee --append /etc/X11/xorg.conf.d/90-default.conf <<- EOF

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
  swtpm
  virt-manager
)
sudo pacman --sync --refresh "${packages[@]}"
sudo systemctl enable libvirtd.service
sudo usermod --append --groups libvirt "${USER}"

application-launcher --add "virt-manager" "/usr/bin/virt-manager"
```

#### Firewall

```bash
sudo nft --file /etc/nftables.conf

sudo nft add rule inet default input iifname "virbr*" udp dport { 53, 67 } accept
sudo nft add rule inet default forward ct state vmap { invalid : drop, established : accept, related : accept }
sudo nft add rule inet default forward iifname { "docker*", "virbr*" } accept

printf "destroy table inet default\n%s\n" "$(sudo nft list table inet default | sed "s/\t/    /g")" | sudo tee /etc/nftables.conf
```
