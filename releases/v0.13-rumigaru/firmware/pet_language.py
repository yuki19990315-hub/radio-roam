"""Display-only localization; saved IDs and battle rules remain compatible."""
LABELS = {
    'AURI': 'アウリ', 'GO': 'サガス', 'MENU': 'メニュー',
    'REST': 'ヤスム', 'TRAIN': 'レンシュウ', 'DEX': 'ズカン',
    'BACK': 'モドル', 'NEXT': 'ツギ', 'SCAN TO': 'スキャンで',
    'COLLECT': 'あつめよう', 'HIT': 'コウゲキ', 'SCAN': 'スキャン',
    'HP': 'カイフク', 'RUN': 'ニゲル', 'OK': 'つぎへ',
    'ZAP': 'スパーク', 'BITE': 'かみつく', 'CLAW': 'ひっかく', 'TAIL': 'しっぽ',
    'YOUR TURN': 'どうする？', 'LOCKED': 'まだつかえない', 'DEX FULL': 'ズカンがいっぱい',
    'NO ITEMS': 'アイテムがない', 'HP FULL': 'たいりょくまんたん',
    'ESCAPED': 'にげきった！', 'VICTORY!': 'かった！', 'GOT AURI!': 'なかまになった！',
    'REST TO HEAL': 'やすんでかいふく', 'REST FIRST': 'さきにやすもう',
    'SCAN FAILED': 'たんさくエラー', 'NO SIGNAL': 'でんぱがない',
    'TRY NEW AREA': 'べつのばしょへ', 'SEARCHING': 'たんさくちゅう',
    'WI-FI': 'でんぱをさがす', 'SAVE RETRY': 'ほぞんリトライ'
}


def japanese(value):
    if value in LABELS:
        return LABELS[value]
    for prefix, translated in (('LV ', 'レベル '), ('FOE ', 'テキ '), ('DEX ', 'ズカン '),
                               ('HIT -', 'ダメージ '), ('OUCH -', 'いたい！ '),
                               ('SCAN ', 'スキャン '), ('HEAL +', 'かいふく +'),
                               ('EXP +', 'けいけんち +'), ('ITEM +', 'アイテム +'),
                               ('HP', 'たいりょく ')):
        if value.startswith(prefix):
            return translated + value[len(prefix):]
    return value
