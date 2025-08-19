"""
Менеджер для ротации YouTube API ключей
"""

import time
from typing import List, Optional
from djspyt import keys

class YouTubeKeyManager:
    """Менеджер для управления и ротации YouTube API ключей"""
    
    def __init__(self):
        self.keys = keys.YOUTUBE_API_KEYS.copy()
        self.current_key_index = 0
        self.failed_keys = {}  # {key: timestamp} - ключи, которые не работают
        self.key_cooldown = 3600  # 1 час в секундах - время блокировки ключа после ошибки
        
    def get_current_key(self) -> Optional[str]:
        """Получить текущий активный ключ"""
        if not self.keys:
            return None
        return self.keys[self.current_key_index]
    
    def mark_key_failed(self, failed_key: str, error_message: str = ""):
        """Пометить ключ как неработающий"""
        self.failed_keys[failed_key] = {
            'timestamp': time.time(),
            'error': error_message
        }
        print(f"❌ Ключ API помечен как неработающий: {failed_key[:10]}...")
        if error_message:
            print(f"   Ошибка: {error_message}")
        
        # Переключаемся на следующий ключ
        self._switch_to_next_key()
    
    def _switch_to_next_key(self):
        """Переключиться на следующий доступный ключ"""
        original_index = self.current_key_index
        
        # Ищем следующий рабочий ключ
        for attempt in range(len(self.keys)):
            self.current_key_index = (self.current_key_index + 1) % len(self.keys)
            current_key = self.keys[self.current_key_index]
            
            # Проверяем, не заблокирован ли ключ
            if current_key in self.failed_keys:
                failed_time = self.failed_keys[current_key]['timestamp']
                if time.time() - failed_time < self.key_cooldown:
                    continue  # Ключ еще заблокирован
                else:
                    # Разблокируем ключ
                    del self.failed_keys[current_key]
                    print(f"✅ Ключ API разблокирован: {current_key[:10]}...")
            
            if self.current_key_index != original_index:
                print(f"🔄 Переключение на ключ API: {current_key[:10]}...")
            return
        
        # Если все ключи заблокированы
        print("❌ Все ключи API заблокированы или недоступны")
    
    def get_available_keys_count(self) -> int:
        """Получить количество доступных ключей"""
        available = 0
        for key in self.keys:
            if key not in self.failed_keys:
                available += 1
            elif time.time() - self.failed_keys[key]['timestamp'] >= self.key_cooldown:
                available += 1
        return available
    
    def get_status_info(self) -> dict:
        """Получить информацию о статусе ключей"""
        total_keys = len(self.keys)
        available_keys = self.get_available_keys_count()
        current_key = self.get_current_key()
        
        return {
            'total_keys': total_keys,
            'available_keys': available_keys,
            'current_key': current_key[:10] + "..." if current_key else None,
            'failed_keys': len(self.failed_keys)
        }

# Глобальный экземпляр менеджера
key_manager = YouTubeKeyManager()
