-- Инициализация базы данных
-- Создание начальных данных

-- Создать админа по умолчанию
-- Пароль: changeme123 (хэш bcrypt)
INSERT INTO operators (name, email, password_hash, department, sip_extension, sip_password, is_active, is_available)
VALUES (
    'Администратор',
    'admin@example.com',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5aeS7VNLfD/uG',
    'admin',
    '100',
    'pass100',
    true,
    true
)
ON CONFLICT (email) DO NOTHING;

-- Правила маршрутизации по умолчанию
INSERT INTO routing_rules (name, keywords, intent, route_to, priority, is_active)
VALUES
    ('Продажи', '["купить", "заказ", "продажа", "стоимость", "цена"]', 'sales', 'sales', 1, true),
    ('Поддержка', '["проблема", "не работает", "ошибка", "поломка", "помощь"]', 'support', 'support', 2, true),
    ('Бухгалтерия', '["оплата", "счет", "платеж", "возврат", "деньги"]', 'billing', 'billing', 3, true),
    ('AI Консультант', '[]', 'ai_consultant', 'ai_consultant', 0, true)
ON CONFLICT DO NOTHING;

