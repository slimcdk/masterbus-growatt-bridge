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


Device ID: 3678971, Name: DIS SmartRemote, Article Number: 77010500
  Monitoring Groups (1):
    Group 0: General
      Fields (1):
        Field 3: Tilsluttet enhed () = N/A

Device ID: 4292345, Name: DSI Digital in, Article Number: 77030900
  Monitoring Groups (1):
    Group 0: General
      Fields (6):
        Field 0: State () = On
        Field 3: Battery on () = False
        Field 6: Battery off () = False
        Field 9: Switch 3 () = False
        Field 12: Switch 4 () = False
        Field 1: Disabled () = False

Device ID: 7165655, Name: BAT 4, Article Number: 66025000
  Monitoring Groups (1):
    Group 0: General
      Fields (11):
        Field 0: State of charge (%) = 59.154457092285156
        Field 4: Time remaining () = N/A
        Field 3: Cap. consumed (Ah) = 58.817588806152344
        Field 1: Battery (V) = 26.520000457763672
        Field 2: Battery (A) = -1.8614842891693115
        Field 5: Battery (°C) = 24.760000228881836
        Field 94: Time () = N/A
        Field 95: Date () = N/A
        Field 117: Close relay () = False
        Field 119: Open relay () = False
        Field 167: Stop charge () = False

Device ID: 7163596, Name: BAT 2, Article Number: 66025000
  Monitoring Groups (1):
    Group 0: General
      Fields (11):
        Field 0: State of charge (%) = 86.17843627929688
        Field 4: Time remaining () = N/A
        Field 3: Cap. consumed (Ah) = 19.903030395507812
        Field 1: Battery (V) = 26.503999710083008
        Field 2: Battery (A) = -0.47949710488319397
        Field 5: Battery (°C) = 25.299999237060547
        Field 94: Time () = N/A
        Field 95: Date () = N/A
        Field 117: Close relay () = False
        Field 119: Open relay () = False
        Field 167: Stop charge () = False

Device ID: 7098059, Name: BAT 6, Article Number: 66025000
  Monitoring Groups (1):
    Group 0: General
      Fields (11):
        Field 0: State of charge (%) = 87.02766418457031
        Field 4: Time remaining () = N/A
        Field 3: Cap. consumed (Ah) = 18.680160522460938
        Field 1: Battery (V) = 26.541000366210938
        Field 2: Battery (A) = -0.9151052832603455
        Field 5: Battery (°C) = 23.790000915527344
        Field 94: Time () = N/A
        Field 95: Date () = N/A
        Field 117: Close relay () = False
        Field 119: Open relay () = False
        Field 167: Stop charge () = False

Device ID: 7198401, Name: BAT 3, Article Number: 66025000
  Monitoring Groups (1):
    Group 0: General
      Fields (11):
        Field 0: State of charge (%) = 86.32770538330078
        Field 4: Time remaining () = N/A
        Field 3: Cap. consumed (Ah) = 19.688095092773438
        Field 1: Battery (V) = 26.547000885009766
        Field 2: Battery (A) = -1.7845594882965088
        Field 5: Battery (°C) = 24.920000076293945
        Field 94: Time () = N/A
        Field 95: Date () = N/A
        Field 117: Close relay () = False
        Field 119: Open relay () = False
        Field 167: Stop charge () = False

Device ID: 7126743, Name: BAT 5, Article Number: 66025000
  Monitoring Groups (1):
    Group 0: General
      Fields (11):
        Field 0: State of charge (%) = 74.50288391113281
        Field 4: Time remaining () = N/A
        Field 3: Cap. consumed (Ah) = 36.715850830078125
        Field 1: Battery (V) = 26.534000396728516
        Field 2: Battery (A) = -0.9397886991500854
        Field 5: Battery (°C) = 23.950000762939453
        Field 94: Time () = N/A
        Field 95: Date () = N/A
        Field 117: Close relay () = False
        Field 119: Open relay () = False
        Field 167: Stop charge () = False

Device ID: 7165674, Name: BAT 1, Article Number: 66025000
  Monitoring Groups (2):
    Group 0: Cluster
      Fields (7):
        Field 0: State of charge (%) = 79.84740447998047
        Field 4: Time remaining () = N/A
        Field 3: Cap. consumed (Ah) = 87.05919647216797
        Field 1: Battery (V) = 53.07200241088867
        Field 2: Battery (A) = -3.27522349357605
        Field 5: Battery (°C) = 25.5
        Field 168: Stop charge () = False
    Group 1: Battery
      Fields (11):
        Field 136: State of charge (%) = 85.8932876586914
        Field 137: Time remaining () = N/A
        Field 138: Cap. consumed (Ah) = 20.313674926757812
        Field 139: Battery (V) = 26.567001342773438
        Field 140: Battery (A) = -0.5695388317108154
        Field 141: Battery (°C) = 25.299999237060547
        Field 94: Time () = N/A
        Field 95: Date () = N/A
        Field 117: Close relay () = False
        Field 119: Open relay () = False
        Field 167: Stop charge () = False

Device ID: 2667145, Name: CHG Mass Charger, Article Number: 40040506
  Monitoring Groups (2):
    Group 0: General
      Fields (5):
        Field 13: Device state () = Charging
        Field 21: On/Stand-by () = True
        Field 20: Max. current (%) = 100.0
        Field 18: State () = Bulk
        Field 17: Charger temp (°C) = 22.0
    Group 1: Output
      Fields (4):
        Field 24: Battery name () = House bank
        Field 14: Battery voltage (V) = 52.99803161621094
        Field 15: Battery current (A) = 30.426692962646484
        Field 16: Bat. temperature (°C) = nan