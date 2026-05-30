#!/bin/bash
# Marlboro Bot — auto-restart wrapper
# Перезапускает бота автоматически при любом крэше

echo "🚀 Запуск Marlboro Bot с авто-рестартом..."

while true; do
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ▶️ Старт бота..."
    python main.py
    EXIT_CODE=$?
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️ Бот завершился с кодом $EXIT_CODE"
    if [ $EXIT_CODE -eq 0 ]; then
        echo "Чистое завершение. Перезапуск через 3 сек..."
    else
        echo "Крэш! Перезапуск через 5 сек..."
        sleep 2
    fi
    sleep 3
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 🔄 Перезапуск..."
done
