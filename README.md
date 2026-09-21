# owl-data（紹介ページの自動更新データ）

- 紹介ページ https://wiseowl-cafe.netlify.app/ が読み込む `data.json` を置く場所です。
- 中身は、noteとSubstackの、もともと公開されている情報だけです（鍵や個人情報は入っていません）。
- `scripts/update_data.py` が、noteのマガジン記事数・新着と、Substackの新着を読みます。
- `.github/workflows/update.yml` が、6時間ごとに実行し、**内容が変わった時だけ**保存します。
- このデータの更新は、Netlifyの公開（クレジット消費）を起こしません。ページ側が、ここのデータを直接読み込むためです。
- 紹介ページ本体は、別の箱 wiseowllab/owl-site（非公開）にあります。
