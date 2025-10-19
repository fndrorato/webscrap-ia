#!/usr/bin/env python3
"""
Script para testar se o OracleAuthBackend está configurado corretamente
"""
import os
import django

# Configurar Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'seu_projeto.settings')  # AJUSTAR!
django.setup()

from django.conf import settings
from django.contrib.auth import authenticate

print("="*60)
print("TESTE DE CONFIGURAÇÃO DO AUTHENTICATION BACKEND")
print("="*60)

# 1. Verificar settings
print("\n[1] Verificando AUTHENTICATION_BACKENDS no settings.py...")
backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
print(f"Backends configurados: {len(backends)}")
for i, backend in enumerate(backends, 1):
    print(f"  {i}. {backend}")
    if 'OracleAuthBackend' in backend:
        print("     ✅ OracleAuthBackend encontrado!")

if not any('OracleAuthBackend' in b for b in backends):
    print("\n❌ ERRO: OracleAuthBackend NÃO está em AUTHENTICATION_BACKENDS!")
    print("   Adicione isto no settings.py:")
    print("   AUTHENTICATION_BACKENDS = [")
    print("       'authentication.backends.OracleAuthBackend',")
    print("       'django.contrib.auth.backends.ModelBackend',")
    print("   ]")
    exit(1)

# 2. Verificar configurações Oracle
print("\n[2] Verificando configurações Oracle...")
oracle_host = getattr(settings, 'ORACLE_HOST', None)
oracle_port = getattr(settings, 'ORACLE_PORT', None)
oracle_service = getattr(settings, 'ORACLE_SERVICE_NAME', None)

print(f"  ORACLE_HOST: {oracle_host}")
print(f"  ORACLE_PORT: {oracle_port}")
print(f"  ORACLE_SERVICE_NAME: {oracle_service}")

if not all([oracle_host, oracle_port, oracle_service]):
    print("\n❌ ERRO: Configurações Oracle não encontradas no settings.py!")
    print("   Adicione isto no settings.py:")
    print("   ORACLE_HOST = config('ORACLE_HOST', default='192.168.10.25')")
    print("   ORACLE_PORT = config('ORACLE_PORT', default='1521')")
    print("   ORACLE_SERVICE_NAME = config('ORACLE_SERVICE_NAME', default='orcl')")
    exit(1)

# 3. Testar autenticação
print("\n[3] Testando autenticação...")
print("\n⚠️  Digite as credenciais Oracle para testar:")
username = input("Username: ").strip()
password = input("Password: ").strip()

if not username or not password:
    print("❌ Username e password são obrigatórios!")
    exit(1)

print(f"\nChamando authenticate(username='{username}', password='***')...")
print("="*60)

user = authenticate(username=username, password=password)

print("="*60)

if user:
    print(f"\n✅ AUTENTICAÇÃO BEM-SUCEDIDA!")
    print(f"   User ID: {user.id}")
    print(f"   Username: {user.username}")
    print(f"   Is Active: {user.is_active}")
    print(f"   Is Staff: {user.is_staff}")
    print("\n🎉 O backend está funcionando corretamente!")
else:
    print(f"\n❌ AUTENTICAÇÃO FALHOU!")
    print("   Possíveis causas:")
    print("   1. Credenciais Oracle incorretas")
    print("   2. Conta Oracle bloqueada")
    print("   3. Problema de conectividade com Oracle")
    print("   4. Backend não está sendo chamado (verifique logs acima)")

print("\n" + "="*60)