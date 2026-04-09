"""
Тесты для системы управления эффектами субтитров
"""
import sys
sys.path.insert(0, 'e:/Neyro/VideoCaptioner')

from app.core.subtitle_processor.effect_manager import (
    EffectManager,
    SubtitleEffect,
    EffectConfig
)


def test_all_effects():
    """Тестирование всех эффектов"""
    manager = EffectManager()
    
    test_text = "Привет мир"
    time_position = 1.0
    
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ЭФФЕКТОВ СУБТИТРОВ")
    print("=" * 60)
    
    effects_to_test = [
        (SubtitleEffect.NONE, "NONE"),
        (SubtitleEffect.FADE_IN, "FADE_IN"),
        (SubtitleEffect.FADE_OUT, "FADE_OUT"),
        (SubtitleEffect.FADE_IN_OUT, "FADE_IN_OUT"),
        (SubtitleEffect.BOUNCE, "BOUNCE"),
        (SubtitleEffect.PULSE, "PULSE"),
        (SubtitleEffect.WAVE, "WAVE"),
        (SubtitleEffect.SPIN, "SPIN"),
        (SubtitleEffect.ZOOM_IN, "ZOOM_IN"),
        (SubtitleEffect.SWING, "SWING"),
        (SubtitleEffect.GLITCH, "GLITCH"),
        (SubtitleEffect.TYPEWRITER, "TYPEWRITER"),
        (SubtitleEffect.TWINKLE, "TWINKLE"),
        (SubtitleEffect.RAINBOW, "RAINBOW"),
        (SubtitleEffect.SHINE, "SHINE"),
    ]
    
    print(f"\nТекст для теста: '{test_text}'")
    print(f"Временная позиция: {time_position}")
    print("-" * 60)
    
    for effect_type, name in effects_to_test:
        config = EffectConfig(effect_type=effect_type, duration=2.0, intensity=1.0)
        result = manager.apply_effects_to_subtitle(test_text, config, time_position)
        print(f"\n[{name}]:")
        print(f"  Результат: {result}")
    
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
    print("=" * 60)


def test_typewriter_progression():
    """Тестирование прогрессии эффекта пишущей машинки"""
    manager = EffectManager()
    
    text = "Это тестовое предложение для проверки"
    duration = 3.0
    
    print("\n" + "=" * 60)
    print("ТЕСТ ПРОГРЕССИИ TYPEWRITER")
    print(f"Текст: '{text}'")
    print(f"Длительность: {duration} сек")
    print("-" * 60)
    
    for t in [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        result = manager.generate_typewriter_effect(text, t, duration)
        print(f"t={t:.1f}: '{result}'")
    
    print("=" * 60)


def test_wave_effect():
    """Тестирование волнового эффекта для отдельных слов"""
    manager = EffectManager()
    
    text = "Первое Второе Третье Четвертое"
    config = EffectConfig(effect_type=SubtitleEffect.WAVE, duration=2.0, intensity=1.0)
    
    print("\n" + "=" * 60)
    print("ТЕСТ ВОЛНОВОГО ЭФФЕКТА (по словам)")
    print(f"Текст: '{text}'")
    print("-" * 60)
    
    for t in [0.0, 0.5, 1.0, 1.5]:
        result = manager.apply_effects_to_subtitle(text, config, t)
        print(f"t={t:.1f}: {result}")
    
    print("=" * 60)


if __name__ == "__main__":
    test_all_effects()
    test_typewriter_progression()
    test_wave_effect()
