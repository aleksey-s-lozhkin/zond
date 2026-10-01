#!/usr/bin/env bash
#
# Сборка APK, подписанного тем же ключом, что и выпуски на GitHub.
#
# Зачем отдельный скрипт. `flet build apk` без ключа подписывает сборку
# отладочным ключом, который создаётся заново на каждой машине. Android не
# ставит обновление поверх приложения с другой подписью, поэтому локальная
# сборка не вставала поверх выпущенной, и наоборот.
#
# Ключ создаётся один раз: bash tools/make_signing_key.sh
# Он лежит вне репозитория — в ~/zond-signing.
#
# Запуск:
#     bash tools/build_apk.sh
#     bash tools/build_apk.sh --arch arm64-v8a   # только под arm64
#     bash tools/build_apk.sh --split-per-abi    # отдельный файл на архитектуру
#
# Дополнительные аргументы передаются в flet build без изменений.
#
# Готовый файл: build/apk/zond-ects.apk — его можно ставить поверх
# установленного приложения, как и файл из релиза.

set -euo pipefail

# Путь к файлу с паролями задаётся переменной окружения, а не аргументом:
# остальные аргументы уходят в сборку.
INFO="${ZOND_SIGNING_INFO:-$HOME/zond-signing/данные-ключа.txt}"
KEYSTORE="$HOME/zond-signing/zond-upload.jks"

if [ ! -f "$KEYSTORE" ]; then
    echo "Не найден ключ подписи: $KEYSTORE" >&2
    echo "Создайте его: bash tools/make_signing_key.sh" >&2
    exit 1
fi

if [ ! -f "$INFO" ]; then
    echo "Не найден файл с паролями: $INFO" >&2
    exit 1
fi

# Значения читаются из файла, который создал скрипт создания ключа.
read_value() {
    sed -n "s/^$1:[[:space:]]*//p" "$INFO" | head -1
}

STORE_PASSWORD="$(read_value "Пароль хранилища")"
KEY_PASSWORD="$(read_value "Пароль ключа")"
ALIAS="$(read_value "Псевдоним")"

if [ -z "$STORE_PASSWORD" ] || [ -z "$KEY_PASSWORD" ] || [ -z "$ALIAS" ]; then
    echo "В файле $INFO не хватает паролей или псевдонима." >&2
    exit 1
fi

export FLET_ANDROID_SIGNING_KEY_STORE="$KEYSTORE"
export FLET_ANDROID_SIGNING_KEY_STORE_PASSWORD="$STORE_PASSWORD"
export FLET_ANDROID_SIGNING_KEY_PASSWORD="$KEY_PASSWORD"
export FLET_ANDROID_SIGNING_KEY_ALIAS="$ALIAS"

echo "Подпись: $KEYSTORE (псевдоним $ALIAS)"

if [ -n "${JAVA_HOME:-}" ]; then
    :
elif [ -d "/Applications/Android Studio.app/Contents/jbr/Contents/Home" ]; then
    export JAVA_HOME="/Applications/Android Studio.app/Contents/jbr/Contents/Home"
fi

# Скрипт должен работать и при запуске из другого каталога.
cd "$(dirname "$0")/.."

# flet берётся из окружения проекта: системного может не быть.
FLET=".venv/bin/flet"

if [ ! -x "$FLET" ]; then
    FLET="$(command -v flet || true)"
fi

if [ -z "$FLET" ]; then
    echo "Не найден flet. Активируйте окружение проекта или установите flet." >&2
    exit 1
fi

"$FLET" build apk --yes "$@"
