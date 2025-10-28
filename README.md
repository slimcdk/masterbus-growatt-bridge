# Configure setup for CAN hat https://www.waveshare.com/wiki/2-CH_CAN_FD_HAT
```bash
$ sudo nano /boot/firmware/config.txt
```
```
dtparam=spi=on
dtoverlay=spi1-3cs
dtoverlay=mcp251xfd,spi0-0,interrupt=25
dtoverlay=mcp251xfd,spi1-0,interrupt=24
```



## Automatic creation of CAN buses (can0 = inverter, can1 = masterbus)
```bash
$ sudo nano /etc/systemd/system/can-setup.service
```

```
[Unit]
Description=Set up CAN interfaces can0 and can1
# Wait for the network device drivers to be loaded
After=network.target

[Service]
Type=oneshot
RemainAfterExit=yes

# Initialization for can0 (500k bitrate)
ExecStart=/sbin/ip link set can0 type can bitrate 500000 restart-ms 100
ExecStart=/sbin/ip link set up can0

# Initialization for can1 (250k bitrate)
ExecStart=/sbin/ip link set can1 type can bitrate 250000 restart-ms 100
ExecStart=/sbin/ip link set up can1
 
ExecStop=/sbin/ip link set can0 down
ExecStop=/sbin/ip link set can1 down

[Install]
WantedBy=multi-user.target
```

### Enable the service on boots
```bash
$ sudo systemctl daemon-reload
$ sudo systemctl enable can-setup.service
$ sudo systemctl start can-setup.service
```


# Docker installation https://get.docker.com/

```bash
$ curl -fsSL https://get.docker.com -o install-docker.sh
$ sudo sh install-docker.sh
$ sudo usermod -aG docker $USER
```


```bash
$ docker build -t m2g .
$ docker run -d --privileged --network=host --restart=unless-stopped m2g
```


