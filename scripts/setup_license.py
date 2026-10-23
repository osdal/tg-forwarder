import os
import re
import base64
import json
import datetime
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

def main():
    print("🔐 Генерация ключей безопасности...")

    private_key = Ed25519PrivateKey.generate()
    private_bytes = private_key.private_bytes_raw()
    public_bytes = private_key.public_key().public_bytes_raw()

    private_b64 = base64.b64encode(private_bytes).decode()
    public_b64 = base64.b64encode(public_bytes).decode()

    # 1. Обновляем публичный ключ в config.py
    config_path = "shared/config.py"
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        content = content.replace('PASTE_YOUR_PUBLIC_KEY_HERE', public_b64)
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Публичный ключ добавлен в shared/config.py")

    # 2. Генерируем лицензию Owner
    payload = {
        "client": "Owner",
        "expires": (datetime.datetime.now() + datetime.timedelta(days=36500)).isoformat(),
        "plan": "owner",
        "limits": {"max_sources": -1, "ai_enabled": True, "image_gen_enabled": True},
    }
    payload_b64 = base64.b64encode(json.dumps(payload).encode()).decode()
    signature = private_key.sign(payload_b64.encode())
    signature_b64 = base64.b64encode(signature).decode()
    license_key = f"{payload_b64}.{signature_b64}"

    # 3. Записываем всё в .env
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        if "LICENSE_KEY=" in content:
            content = re.sub(r'LICENSE_KEY=.*', f'LICENSE_KEY={license_key}', content)
        else:
            content += f"\nLICENSE_KEY={license_key}\n"
            
        if "LICENSE_PRIVATE_KEY=" in content:
            content = re.sub(r'LICENSE_PRIVATE_KEY=.*', f'LICENSE_PRIVATE_KEY={private_b64}', content)
        else:
            content += f"LICENSE_PRIVATE_KEY={private_b64}\n"
            
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(content)
        print("✅ Лицензия и приватный ключ прописаны в .env")
    
    print("\n🎉 ГОТОВО! Теперь выполни миграцию и пересобери контейнеры.")

if __name__ == "__main__":
    main()