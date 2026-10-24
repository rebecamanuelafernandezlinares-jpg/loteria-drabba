# Llevar la Lotería DRABBA a una máquina gratis de Oracle Cloud

Resultado: la app queda siempre encendida (sin la espera de ~1 minuto de Render),
con su propia base de datos Postgres, en `https://loteria.hertechnology.co`.

## Antes de empezar: lo que hay que saber

- Oracle pide **tarjeta de crédito para verificar la cuenta**. Si te quedas dentro de los
  recursos "Always Free" no se cobra, pero la tarjeta es obligatoria.
- La **región principal (home region) no se puede cambiar** después. Elige la más cercana a ti.
  Los recursos gratis solo son gratis en esa región.
- A veces sale el error **"Out of host capacity"** al crear la máquina. Prueba otro
  "availability domain", o reintenta más tarde.
- Oracle **puede reclamar máquinas gratis que considere inactivas** (uso de CPU y red
  por debajo del 20 % durante 7 días). Esta app usa muy poco, así que es un riesgo real.
  Por eso el paso 8 (respaldos) no es opcional.

## 1. Crear la cuenta
1. Entra a oracle.com/cloud/free y crea la cuenta (elige bien la región principal).
2. Espera el correo de que la cuenta está activa.

## 2. Crear la máquina virtual
1. Menú → **Compute → Instances → Create instance**.
2. Imagen: **Ubuntu 22.04 o 24.04**.
3. Forma (shape): lo más cómodo es **Ampere A1 (VM.Standard.A1.Flex)** con 1 o 2 OCPU y 6 GB
   de memoria. Si no hay capacidad, sirve la **VM.Standard.E2.1.Micro** (1 GB; alcanza, pero justo).
4. Red: deja marcado **asignar IP pública**.
5. Llaves SSH: deja que Oracle genere el par y **descarga la llave privada** (.key). Guárdala bien.
6. Crea la instancia y copia su **IP pública**.

## 3. Abrir los puertos 80 y 443
1. En la instancia → su **Subnet → Security List → Add Ingress Rules**.
2. Agrega dos reglas: origen `0.0.0.0/0`, protocolo TCP, puerto destino `80`, y otra con `443`.

## 4. Apuntar el dominio
En el panel donde administras `hertechnology.co`, crea un registro **A**:
`loteria` → la IP pública de la máquina. (Si usas Cloudflare, déjalo en "solo DNS", sin nube naranja,
mientras se emite el certificado.)

## 5. Entrar a la máquina y preparar Docker
Desde PowerShell (cambia la ruta de la llave y la IP):

```
ssh -i C:\ruta\a\tu-llave.key ubuntu@IP_PUBLICA
```

Ya dentro:

```
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Ubuntu en Oracle trae un firewall interno que también hay que abrir:
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo apt-get install -y iptables-persistent && sudo netfilter-persistent save
exit
```

Vuelve a entrar por SSH (para que se aplique el grupo docker).

## 6. Bajar el proyecto y configurarlo

```
git clone https://github.com/rebecamanuelafernandezlinares-jpg/loteria-drabba.git
cd loteria-drabba
git checkout oracle-deploy      # quítalo cuando la rama ya esté en main
cp deploy/.env.example .env
nano .env                       # llena las 4 variables y guarda (Ctrl+O, Enter, Ctrl+X)
```

## 7. Copiar los datos desde Render (para no perder nada)
1. En Render abre tu base de datos y copia la **External Database URL**.
2. Mira la versión de Postgres que muestra Render. Si no es 16, cambia `postgres:16-alpine`
   en `docker-compose.yml` por esa misma versión mayor antes de seguir.
3. En el servidor, levanta SOLO la base de datos y copia los datos:

```
docker compose up -d db
docker run --rm postgres:16-alpine pg_dump --no-owner --no-acl "PEGA_AQUI_LA_EXTERNAL_URL" \
  | docker compose exec -T db psql -U loteria loteria
```

4. Ahora sí levanta todo:

```
docker compose up -d --build
docker compose ps
```

5. Abre `https://loteria.hertechnology.co`. Deben salir tus rifas y números.
   Prueba **Buscar** con un código CUS.

Deja Render funcionando unos días como respaldo y bórralo cuando estés tranquilo.

## 8. Respaldos diarios (importante)

```
crontab -e
```

Agrega esta línea (respaldo todos los días a las 3:00 a. m.):

```
0 3 * * * /home/ubuntu/loteria-drabba/deploy/backup.sh
```

Los respaldos quedan en `~/respaldos-loteria`. Descarga uno de vez en cuando a tu
computador (con `scp`), porque si Oracle reclamara la máquina se llevaría los respaldos también.

## Actualizar la app más adelante

```
cd ~/loteria-drabba && git pull && docker compose up -d --build
```
