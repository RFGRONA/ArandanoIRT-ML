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

echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

echo "SWAP configurado exitosamente."
swapon --show
