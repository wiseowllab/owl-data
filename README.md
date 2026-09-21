# owl-data（紹介ページの自動更新データ）

- 紹介ページ https://wiseowl-cafe.netlify.app/ が読み込む `data.json` を置く場所です。
- 中身は、noteとSubstackの、もともと公開されている情報だけです（鍵や個人情報は入っていません）。
- `scripts/update_data.py` が、noteのマガジン記事数・新着と、Substackの新着を読みます。
- `.github/workflows/update.yml` が、1日2回実行し、**内容が変わった時だけ**保存します。
- このデータの更新は、Netlifyの公開（クレジット消費）を起こしません。ページ側が、ここのデータを直接読み込むためです。
- 紹介ページ本体は、別の箱 wiseowllab/owl-site（非公開）にあります。

## 更新の担当（2026-09-22）
| 対象 | 担当 | いつ |
|---|---|---|
| note（新着・マガジン記事数） | GitHub Actions | 毎日 日本時間12:10と17:10ごろ（GitHubの都合で遅れることがある。手動実行も可） |
| Substack（記事・Notes） | このパソコン（タスクスケジューラ `OwlData-SubstackUpdate`、`pc_update.ps1`） | ログオンの2分後／毎日20時（取り逃した時は起動後すぐ） |

- Substackは、GitHubのサーバーからのアクセスを拒否する（403）ため、パソコンから読む。
- パソコンが起動していない間は、Substackの部分は更新されない。記録は `logs\pc_update.log`（GitHubには送らない）。
- 予定の削除：`Unregister-ScheduledTask -TaskName OwlData-SubstackUpdate -Confirm:$false`
