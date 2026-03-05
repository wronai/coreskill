#!/bin/bash
# CoreSkill environment activation script
echo "🚀 Aktywuję środowisko CoreSkill..."
source /home/tom/miniconda3/etc/profile.d/conda.sh
conda activate coreskill
echo "✅ Środowisko gotowe!"
echo "📝 Dostępne komendy:"
echo "   taskfile run start    - Uruchom CoreSkill"
echo "   taskfile run dev      - Tryb deweloperski"
echo "   taskfile run test     - Uruchom testy"
echo "   taskfile list         - Pokaż wszystkie komendy"
