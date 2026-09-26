#!/usr/bin/env bash
#
# Создание ключа подписи для Android — выполняется один раз.
#
# Зачем. По умолчанию `flet build apk` подписывает сборку отладочным ключом,
# который генерируется заново на каждой машине и на каждом запуске GitHub
# Actions. Android не устанавливает обновление поверх приложения, подписанного
# другим ключом: выдаёт «signatures do not match». То есть без своего ключа
# каждую новую версию пришлось бы ставить только после удаления прежней —
# вместе со всеми данными.
#
# Ключ создаётся здесь и больше не меняется. Потеряете его — обновления
# перестанут устанавливаться поверх: придётся либо восстанавливать ключ из
# копии, либо просить пользователей удалять приложение.
#
# Запуск:
#     bash tools/make_signing_key.sh
#
# Скрипт создаст:
#     ~/zond-signing/zond-upload.jks   — сам ключ (храните копию отдельно)
#     ~/zond-signing/данные-ключа.txt  — пароли и значения для секретов GitHub
#
# Оба файла лежат вне репозитория и в git не попадают.

set -euo pipefail

TARGET_DIR="${1:-$HOME/zond-signing}"
KEYSTORE="$TARGET_DIR/zond-upload.jks"
INFO="$TARGET_DIR/данные-ключа.txt"
ALIAS="zond"
DAYS=10000

JAVA_HOME="${JAVA_HOME:-/Applications/Android Studio.app/Contents/jbr/Contents/Home}"
KEYTOOL="$JAVA_HOME/bin/keytool"

if [ ! -x "$KEYTOOL" ]; then
    KEYTOOL="$(command -v keytool || true)"
fi

if [ -z "$KEYTOOL" ] || [ ! -x "$KEYTOOL" ]; then
    echo "Не найден keytool. Укажите JAVA_HOME на каталог JDK." >&2
    exit 1
fi

if [ -f "$KEYSTORE" ]; then
    echo "Ключ уже есть: $KEYSTORE" >&2
    echo "Удалять и создавать заново нельзя — обновления перестанут устанавливаться." >&2
    exit 1
fi

mkdir -p "$TARGET_DIR"

STORE_PASSWORD="$(openssl rand -base64 24 | tr -d '/+=' | cut -c1-24)"
KEY_PASSWORD="$STORE_PASSWORD"

"$KEYTOOL" -genkeypair \
    -keystore "$KEYSTORE" \
    -alias "$ALIAS" \
    -keyalg RSA \
    -keysize 4096 \
    -validity "$DAYS" \
    -storepass "$STORE_PASSWORD" \
    -keypass "$KEY_PASSWORD" \
    -dname "CN=ZOND ECTS, OU=Mobile, O=pyconstrictor, L=Moscow, C=RU"

BASE64="$(base64 -i "$KEYSTORE" | tr -d '\n')"

cat > "$INFO" <<INFO_END
Ключ подписи Android для приложения «ЗОНД: ECTS»
================================================

Файл ключа: $KEYSTORE
Псевдоним:  $ALIAS
Срок:       $DAYS дней

Пароль хранилища: $STORE_PASSWORD
Пароль ключа:     $KEY_PASSWORD

Сделайте копию файла ключа в надёжном месте. Если он потеряется, новую версию
нельзя будет установить поверх прежней — только удалив приложение вместе с
данными.

Секреты GitHub
--------------
Откройте: репозиторий → Settings → Secrets and variables → Actions →
New repository secret. Добавьте четыре секрета:

1. ANDROID_KEYSTORE_BASE64
$BASE64

2. ANDROID_KEYSTORE_PASSWORD
$STORE_PASSWORD

3. ANDROID_KEY_PASSWORD
$KEY_PASSWORD

4. ANDROID_KEY_ALIAS
$ALIAS

Сборка на своём компьютере
--------------------------
Подписывать локальные сборки тем же ключом, чтобы они были совместимы с
выпущенными:

    export FLET_ANDROID_SIGNING_KEY_STORE="$KEYSTORE"
    export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD="$STORE_PASSWORD"
    export FLET_ANDROID_SIGNING_KEY_PASSWORD="$KEY_PASSWORD"
    export FLET_ANDROID_SIGNING_KEY_ALIAS="$ALIAS"
    flet build apk --yes
INFO_END

chmod 600 "$KEYSTORE" "$INFO"

echo "Ключ создан: $KEYSTORE"
echo "Пароли и значения для секретов: $INFO"
echo
echo "Дальше: добавьте четыре секрета в GitHub — они перечислены в файле."
