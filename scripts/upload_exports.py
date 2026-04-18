#!/usr/bin/env python3
"""
CLI для массовой загрузки Telegram JSON экспортов в RAG систему.

Использование:
    python upload_exports.py --source my-telegram --files file1.json file2.json ...
    python upload_exports.py --source my-telegram --dir /path/to/exports/
    python upload_exports.py --source my-telegram --files *.json --watch

Пример для 18 файлов:
    python upload_exports.py --source my-telegram --dir ./telegram_exports/ --watch
"""

import argparse
import json
import sys
import time
from pathlib import Path
from typing import List, Optional
import requests


DEFAULT_API_URL = "http://localhost:8001/api"


def upload_files(
    files: List[Path],
    source_slug: str,
    api_url: str = DEFAULT_API_URL,
    watch: bool = False
) -> dict:
    """
    Загрузить несколько файлов через bulk_upload API.
    
    Args:
        files: список путей к JSON файлам
        source_slug: slug TelegramSource
        api_url: базовый URL API
        watch: отслеживать прогресс после загрузки
    
    Returns:
        результат bulk_upload
    """
    url = f"{api_url}/import-jobs/bulk_upload/"
    
    # Подготовка файлов
    file_tuples = []
    for f in files:
        file_tuples.append(
            ('files', (f.name, open(f, 'rb'), 'application/json'))
        )
    
    data = {'source_slug': source_slug}
    
    print(f"Загружаем {len(files)} файлов...")
    for f in files:
        print(f"  - {f.name}")
    
    try:
        response = requests.post(url, data=data, files=file_tuples)
        response.raise_for_status()
        result = response.json()
        
        print(f"\n✅ Загрузка завершена!")
        print(f"   Batch ID: {result.get('batch_id')}")
        print(f"   Успешно: {result.get('successful')} файлов")
        print(f"   Ошибок: {result.get('failed')} файлов")
        print(f"   Всего сообщений: {result.get('total_messages')}")
        
        if watch:
            watch_progress(result.get('batch_id'), api_url)
        
        return result
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка загрузки: {e}")
        if hasattr(e.response, 'text'):
            print(f"   Ответ сервера: {e.response.text}")
        sys.exit(1)
    finally:
        for _, (fp, _) in file_tuples:
            fp.close()


def watch_progress(batch_id: str, api_url: str = DEFAULT_API_URL, interval: int = 5):
    """
    Отслеживать прогресс батча в реальном времени.
    
    Args:
        batch_id: ID батча загрузки
        api_url: базовый URL API
        interval: интервал обновления в секундах
    """
    url = f"{api_url}/import-jobs/batch_status/"
    
    print(f"\n📊 Отслеживание прогресса батча {batch_id}...")
    print("=" * 60)
    
    while True:
        try:
            response = requests.get(url, params={'batch_id': batch_id})
            response.raise_for_status()
            status = response.json()
            
            total = status.get('total', 0)
            completed = status.get('completed', 0)
            processing = status.get('processing', 0)
            failed = status.get('failed', 0)
            overall_progress = status.get('overall_progress', 0)
            
            # Очистка предыдущей строки (для анимации)
            print(f"\r{' ' * 60}\r", end='')
            
            # Вывод прогресса
            bar_length = 40
            filled = int(bar_length * overall_progress / 100)
            bar = '█' * filled + '░' * (bar_length - filled)
            
            print(f"[{bar}] {overall_progress}% | {completed}/{total} файлов | Обработка: {processing} | Ошибок: {failed}", end='', flush=True)
            
            # Проверка завершения
            if processing == 0 and completed + failed == total:
                print(f"\n\n{'=' * 60}")
                print(f"✅ Обработка завершена!")
                print(f"   Успешно: {completed}")
                print(f"   Ошибок: {failed}")
                
                # Детали по каждому файлу
                print("\n📁 Детали по файлам:")
                for job in status.get('jobs', []):
                    filename = job.get('filename', 'unknown')
                    job_status = job.get('status', 'unknown')
                    progress = job.get('progress_percent', 0)
                    print(f"   {filename}: {job_status} ({progress}%)")
                
                break
            
            time.sleep(interval)
            
        except KeyboardInterrupt:
            print(f"\n\n⚠️ Отслеживание прервано. Batch ID: {batch_id}")
            print(f"   Для продолжения отслеживания:")
            print(f"   python upload_exports.py --watch-only {batch_id}")
            sys.exit(0)
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Ошибка получения статуса: {e}")
            time.sleep(interval)


def watch_only(batch_id: str, api_url: str = DEFAULT_API_URL, interval: int = 5):
    """Только отслеживание существующего батча."""
    watch_progress(batch_id, api_url, interval)


def get_queue_status(api_url: str = DEFAULT_API_URL):
    """Получить общий статус очереди."""
    url = f"{api_url}/import-jobs/queue_status/"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        status = response.json()
        
        print("📊 Статус очереди импорта:")
        print(f"   В очереди: {status.get('queued', 0)}")
        print(f"   Обрабатывается: {status.get('processing', 0)}")
        print(f"   Завершено: {status.get('done', 0)}")
        print(f"   Ошибок: {status.get('failed', 0)}")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description='Загрузка Telegram JSON экспортов в RAG систему',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры:
  # Загрузка 18 файлов с отслеживанием:
  python upload_exports.py --source my-telegram --dir ./exports/ --watch
  
  # Загрузка конкретных файлов:
  python upload_exports.py --source my-telegram --files 1.json 2.json 3.json
  
  # Только отслеживание существующего батча:
  python upload_exports.py --watch-only 20260419_123456_789000
  
  # Статус очереди:
  python upload_exports.py --queue-status
        """
    )
    
    parser.add_argument('--source', '-s', help='Telegram source slug')
    parser.add_argument('--files', '-f', nargs='+', help='JSON файлы для загрузки')
    parser.add_argument('--dir', '-d', help='Директория с JSON файлами')
    parser.add_argument('--api-url', default=DEFAULT_API_URL, help=f'URL API (default: {DEFAULT_API_URL})')
    parser.add_argument('--watch', '-w', action='store_true', help='Отслеживать прогресс после загрузки')
    parser.add_argument('--watch-only', metavar='BATCH_ID', help='Только отслеживание существующего батча')
    parser.add_argument('--queue-status', '-q', action='store_true', help='Показать статус очереди')
    parser.add_argument('--interval', '-i', type=int, default=5, help='Интервал обновления (сек)')
    
    args = parser.parse_args()
    
    # Только статус очереди
    if args.queue_status:
        get_queue_status(args.api_url)
        return
    
    # Только отслеживание
    if args.watch_only:
        watch_only(args.watch_only, args.api_url, args.interval)
        return
    
    # Проверка обязательных аргументов
    if not args.source:
        print("❌ Нужно указать --source (Telegram source slug)")
        sys.exit(1)
    
    # Сбор файлов
    files = []
    
    if args.files:
        files = [Path(f) for f in args.files]
    elif args.dir:
        dir_path = Path(args.dir)
        if not dir_path.exists():
            print(f"❌ Директория не найдена: {dir_path}")
            sys.exit(1)
        files = list(dir_path.glob('*.json'))
        if not files:
            print(f"❌ JSON файлы не найдены в {dir_path}")
            sys.exit(1)
    else:
        print("❌ Нужно указать --files или --dir")
        sys.exit(1)
    
    # Проверка файлов
    for f in files:
        if not f.exists():
            print(f"❌ Файл не найден: {f}")
            sys.exit(1)
        if not f.name.endswith('.json'):
            print(f"❌ Файл не является JSON: {f}")
            sys.exit(1)
    
    # Загрузка
    upload_files(files, args.source, args.api_url, args.watch)


if __name__ == '__main__':
    main()
