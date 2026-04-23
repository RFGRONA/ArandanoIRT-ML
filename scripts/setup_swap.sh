#!/bin/bash
# script para configurar 2GB de SWAP en Ubuntu

echo "Configurando 2GB de memoria SWAP..."

if swapon --show | grep -q "/swapfile"; then
    echo "El archivo swap ya existe."
    exit 0
fi

sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

if ! grep -Eq '^/swapfile[[:space:]]+none[[:space:]]+swap[[:space:]]+sw[[:space:]]+0[[:space:]]+0$' /etc/fstab; then
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
fi

echo "SWAP configurado exitosamente."
swapon --show
