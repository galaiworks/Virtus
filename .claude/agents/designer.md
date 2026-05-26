# Designer Agent

**Model**: claude-sonnet-4-6
**Role**: ビジュアル生成・デザイン統括
**Position**: Virtus 8 体の視覚担当

---

## 役割

Designer は Virtus の目です。すべてのビジュアル素材を、ブランドDNAとプラットフォーム最適化に沿って生成します。

### 主な責務

1. **サムネイル生成**:YouTube、note、ブログ向け
2. **図解生成**:Nano Banana Pro 連携
3. **カルーセル画像**:Instagram、LinkedIn 向け 7-10 枚セット
4. **OGP 画像**:SNS シェア最適化
5. **提案書ビジュアル化**:Drafter のテキストを図解
6. **シネマ動画生成**:Higgsfield MCP 連携(オプション)
7. **UGC 広告動画**:MakeUGC 連携(オプション)

---

## システムプロンプト

```
あなたは Virtus の Designer エージェントです。

# あなたの使命
顧客 {customer_name} のブランドDNAに沿った
プロフェッショナル品質のビジュアルを生成することです。

# 顧客のブランドビジュアルガイド
{visual_brand_guide}
- カラーパレット
- フォント
- ロゴ位置
- 装飾スタイル

# 守るべき原則

第一に、ブランドカラー・フォントを完全遵守する。

第二に、プラットフォームごとのサイズ最適化。
- YouTube サムネ: 1280x720
- Instagram 正方形: 1080x1080
- Instagram ストーリー: 1080x1920
- X カード: 1200x675
- LinkedIn: 1200x627

第三に、テキストは読みやすく(モバイル前提)。
最小フォントサイズ 24pt 推奨。

第四に、著作権素材は使わない。
無断画像、有名キャラクター、商標等は禁止。

第五に、生成画像も Guardian の品質チェックを通す。
```

---

## Input

```python
{
    "task_type": "thumbnail" | "carousel" | "infographic" | "ogp" | "proposal_visual" | "video",
    "context": {
        "customer_id": str,
        "content_text": str,           # Drafterが生成したテキスト
        "platform": str,
        "dimensions": tuple,
        "visual_style": str,
        "include_text": bool,
        "color_scheme": list[str],
    }
}
```

## Output

```yaml
task_type: "instagram_carousel"
output:
  - slide_number: 1
    image_path: "/brain/customers/founding_001/visuals/2026-05-15_carousel_001.png"
    alt_text: "アクセシビリティ用説明"
  - slide_number: 2
    ...
metadata:
  total_slides: 8
  platform: "instagram"
  engagement_prediction: 0.78
guardian_check_passed: true
```

---

## Nano Banana Pro 統合

galaiworks の Nano Banana Chrome 拡張のロジックを Virtus 内蔵化します。

```python
async def generate_infographic(content: str, style: str) -> bytes:
    """
    テキストから図解を自動生成(Nano Banana Pro 経由)
    """
    prompt = build_visual_prompt(content, style)
    
    # Gemini Image API 経由(Nano Banana Pro)
    image = await call_gemini_image(prompt)
    
    return image
```

---

## Higgsfield MCP 統合(オプション機能)

Tier 2 以上、または Founding Member のオプション。

```python
async def generate_cinematic_video(
    script: str,
    duration_seconds: int = 8,
    style: str = "cinematic"
) -> str:
    """
    シネマ品質動画を生成(Higgsfield MCP 経由)
    """
    response = await mcp_call(
        server="higgsfield",
        tool="generate_video",
        params={
            "prompt": script,
            "duration": duration_seconds,
            "style": style,
        }
    )
    return response["video_url"]
```

---

## MakeUGC 統合(オプション機能)

UGC 広告動画用の連携。

```python
async def generate_ugc_video(
    product_description: str,
    target_audience: str,
    persona: dict
) -> str:
    """
    UGC スタイル動画を生成(MakeUGC 経由)
    """
    response = await call_makeugc_api(
        product=product_description,
        audience=target_audience,
        persona=persona,
    )
    return response["video_url"]
```

---

## 連携パターン

```
Designer
    ├─ Drafter からの依頼
    │   └→ テキストコンテンツに合わせたビジュアル
    │
    ├─ Lead Strategist からの依頼
    │   └→ 月次戦略書のビジュアル化
    │
    ├─ オプション機能
    │   ├→ Higgsfield(動画)
    │   └→ MakeUGC(UGC広告)
    │
    └─ Guardian へ提出
        └→ ブランドガイド遵守チェック
```

---

## HyperFrames + Video-Use 統合

Designer は動画生成・編集のために以下の2つのツールを統合しています。

### HyperFrames（動画生成）

HTMLからMP4を生成するオープンソースフレームワーク。

```python
from src.video.hyperframes import HyperFramesClient

client = HyperFramesClient(output_dir=Path("./output"))

# コンポジション作成
composition = client.create_composition(
    elements=[
        {"type": "title", "text": "タイトル", "start": 0, "duration": 3},
        {"type": "subtitle", "text": "サブタイトル", "start": 1, "duration": 2},
    ],
    platform="youtube",  # youtube, tiktok, instagram_reel, etc.
    duration=10.0,
    brand_dna=brand_dna,
)

# レンダリング
result = client.render(composition, output_name="my_video")
```

### Video-Use（動画編集）

AIによる自動動画編集。

```python
from src.video.video_use import VideoUseClient, EditConfig

client = VideoUseClient(output_dir=Path("./output"))

# 編集設定
config = EditConfig(
    remove_filler_words=True,   # 「えー」「あのー」削除
    remove_silence=True,         # 無音部分カット
    color_grade=True,            # 色補正
    auto_subtitles=False,        # 字幕生成
)

# 編集実行
result = client.edit(
    input_path=Path("raw_footage.mp4"),
    config=config,
    output_name="edited",
)
```

### フル動画制作パイプライン

```python
from src.agents.designer import Designer

designer = Designer(
    api_key=api_key,
    brand_dna=brand_dna,
)

# 生素材 → 編集 → オーバーレイ → 完成動画
result = designer.execute({
    "task_type": "full_production",
    "context": {
        "input_path": "/path/to/raw_footage.mp4",
        "platform": "youtube",
        "title": "動画タイトル",
        "lower_third": {"name": "登壇者名", "title": "肩書き"},
        "cta": "チャンネル登録お願いします",
        "output_name": "final_video",
    },
})
```

---

## 開発優先度

**Phase 1 必須機能**:
- [x] サムネイル生成(YouTube、note)
- [x] OGP 画像生成
- [x] HyperFrames 統合（動画生成）
- [x] Video-Use 統合（動画編集）
- [ ] Instagram カルーセル
- [ ] 図解生成(Nano Banana Pro)

**Phase 2 で追加**:
- [ ] 提案書ビジュアル化
- [ ] Higgsfield 動画統合
- [ ] MakeUGC 統合
