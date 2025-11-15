import requests
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

API_URL = "https://api-baltic.transparency-dashboard.eu/"
TARGET_DATE = "2025-09-22"
REPORT_ID_AFRR = "activations_afrr"
REPORT_ID_IMBALANCE = "imbalance_volumes_v2"

def get_day_range(date_str:str) -> tuple[str,str]:
    dt = datetime.fromisoformat(date_str)
    start = dt.replace(hour=0, minute=0).strftime("%Y-%m-%dT%H:%M")
    end = dt.replace(hour=23, minute=59).strftime("%Y-%m-%dT%H:%M")
    return start, end

def fetch_data(report_id: str, start_date: str, end_date: str, timezone: str = "EET", timeout: int = 30) -> dict:
    """
    API'den veri çeker. Endpoint: /v1/api/export
    API dokümantasyonuna göre /v1/api/export endpoint'ini kullanıyoruz
    """
    # Tam API URL'ini oluştur (base URL + endpoint) - çift slash'ı önlemek için strip kullan
    # Base URL'in sonunda / varsa kaldır, endpoint'in başında / varsa kaldır
    base = API_URL
    endpoint = "api/v1/export"
    url = f"{base}{endpoint}"
    
    # API'nin beklediği parametreleri hazırla
    params = {
        "id": report_id,  # Hangi raporu çekeceğiz (afrr_activation veya imbalance_volumes_v2)
        "start_date": "2025-09-22T00:00",  # Başlangıç tarihi (format: 2025-09-22T00:00)
        "end_date": "2025-09-22T23:59",  # Bitiş tarihi (format: 2025-09-22T23:59)
        "output_time_zone": timezone,  # Zaman dilimi (EET veya UTC)
        "output_format": "json",  # JSON formatında veri istiyoruz
        "json_header_groups": "0"  # Meta bilgi ekleme (0 = ekleme)
    }
    
    # HTTP headers ekle (bazı API'ler User-Agent ister, 403 hatasını önlemek için)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    # Debug için: hangi URL'ye istek yapıldığını göster
    print(f"[API] GET {url}")
    # Debug için: hangi parametrelerle istek yapıldığını göster
    print(f"[API] Params: id={report_id}, start={start_date}, end={end_date}, tz={timezone}")
    # HTTP GET isteği yap (timeout: 30 saniye - bağlantı koparsa bekleme süresi)
    # Headers ekle (403 hatasını önlemek için)
    resp = requests.get(url, params=params, headers=headers, timeout=timeout)
    # HTTP hata kodları varsa exception fırlat (örn: 404, 500)
    resp.raise_for_status()
    
    # Yanıtın Content-Type'ını kontrol et - JSON mu HTML mi?
    content_type = resp.headers.get("Content-Type", "").lower()
    # Eğer HTML döndüyse (hata sayfası olabilir)
    if "text/html" in content_type or not content_type.startswith("application/json"):
        # HTML yanıtının ilk 500 karakterini göster (hata mesajını görmek için)
        print(f"[API] ERROR: HTML yanıtı alındı! Status: {resp.status_code}")
        print(f"[API] Content-Type: {content_type}")
        print(f"[API] Yanıt (ilk 500 karakter): {resp.text[:500]}")
        # Tam URL'yi göster (tarayıcıda test edebilmek için)
        print(f"[API] Tam URL: {resp.url}")
        raise ValueError(f"API HTML döndürdü (muhtemelen hata sayfası). Status: {resp.status_code}. URL'yi tarayıcıda kontrol et: {resp.url}")
    
    # JSON yanıtı Python dictionary'ye çevir ve döndür
    try:
        return resp.json()
    except ValueError as e:
        # JSON parse hatası - yanıtın içeriğini göster
        print(f"[API] ERROR: JSON parse hatası!")
        print(f"[API] Yanıt (ilk 500 karakter): {resp.text[:500]}")
        raise ValueError(f"API yanıtı JSON değil. Yanıt: {resp.text[:200]}") from e

def parse_to_dataframe(data:dict) -> pd.DataFrame:
    if "data" not in data:
        raise ValueError("Invalid data format: 'data' key not found")
    
    if "timeseries" not in data["data"]:
        raise ValueError("Invalid data format: 'timeseries' key not found in 'data'")
    
    timeseries = data["data"]["timeseries"]

    if not timeseries:
        raise ValueError("No timeseries data available")
    
    records = []
    for item in timeseries:
        timestamp = item.get("from")
        values = item.get("values", [])
        total_value = sum(values) if values else 0.0

        records.append(
            {
                "timestamp": timestamp,
                "value": total_value
            }
        )

    df = pd.DataFrame(records)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc = True , errors='coerce')
    df = df.dropna(subset=["timestamp"]).set_index("timestamp").sort_index()
    return df[["value"]]

def calculate_metrics(afrr_df: pd.DataFrame, imbalance_df: pd.DataFrame) -> pd.DataFrame:
    all_times = afrr_df.index.union(imbalance_df.index).sort_values()

    afrr_aligned = afrr_df.reindex(all_times)
    imbalance_aligned = imbalance_df.reindex(all_times)

    afrr_abs = afrr_aligned["value"].abs()
    imbalance_abs = imbalance_aligned["value"].abs()
    ratio = afrr_abs / imbalance_abs.replace(0, pd.NA)

    metrics = pd.DataFrame({
        "afrr_activation": afrr_aligned["value"],
        "imbalance": imbalance_aligned["value"],
        "ratio_abs": ratio
    }, index=all_times)
   
    return metrics

def create_plots(metrics_df: pd.DataFrame, output_dir: Path, date: str):
    fig,ax = plt.subplots(figsize=(14,6))
    ax.plot(metrics_df.index, metrics_df["afrr_activation"], label="aFRR Activation (MW)", linewidth=1.5,alpha=0.8)
    ax.plot(metrics_df.index, metrics_df["imbalance"], label="Imbalance Volume (MW)", linewidth=1.5,alpha=0.8)
    ax.set_title(f"aFRR Activation vs Imbalance Volume - {date}", fontsize=14, fontweight='bold')
    ax.set_xlabel("Time (UTC)", fontsize=12)
    ax.set_ylabel("Volume", fontsize=12)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    fig.tight_layout()
    fig.savefig(output_dir / "timeseries.png", dpi=150, bbox_inches='tight')
    plt.close(fig)

    #2. Ratio plot
    fig, ax = plt.subplots(figsize=(14,5))
    ratio_clean = metrics_df["ratio_abs"].dropna()
    if len(ratio_clean) > 0:
        ax.plot(ratio_clean.index, ratio_clean.values, color = "green", linewidth=1.5, alpha=0.8)
        ax.set_title("aFRR Activation Ratio to Imbalance  ", fontsize=14, fontweight='bold')
        ax.set_xlabel("Time (UTC)", fontsize=12)
        ax.set_ylabel("Ratio (|aFRR Activation| / |Imbalance|)", fontsize=12)
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)

    fig.tight_layout()
    fig.savefig(output_dir / "ratio.png", dpi=150, bbox_inches='tight')
    plt.close(fig)

def generate_report(metrics_df: pd.DataFrame, output_dir: Path, date: str):
    report_path = output_dir / "assessment.txt"

    afrr_abs = metrics_df["afrr_activation"].abs()
    imbalance_abs = metrics_df["imbalance"].abs()

    total_afrr = metrics_df["afrr_activation"].sum()
    total_imbalance = metrics_df["imbalance"].sum()
    avg_ratio = (afrr_abs.sum() / imbalance_abs.replace(0, pd.NA).sum()) if imbalance_abs.sum() > 0 else None

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 60 + "\n")
        f.write("Task 1: aFRR Activation Assessment Report\n")
        f.write(f"Date: {date}\n")
        f.write("=" * 60 + "\n\n")

        #Summary Metrics
        f.write("SUMMARY METRICS\n")
        f.write("-" * 60 + "\n")
        f.write(f"Total aFRR Activation (MW): {total_afrr:.2f}\n")
        f.write(f"Total Imbalance Volume (MW): {total_imbalance:.2f}\n")
        f.write(f"Average |aFRR Activation| / |Imbalance| Ratio: {avg_ratio:.4f}\n")
        f.write(f"Max aFRR Activation (MW): {metrics_df['afrr_activation'].max():.2f}\n")
        f.write(f"Max Imbalance Volume (MW): {metrics_df['imbalance'].max():.2f}\n")
    

        f.write("THEORETICAL BACKGROUND\n")
        f.write("-" * 60 + "\n")
        f.write("aFRR (automatic Frequency Restoration Reserve) is a secondary reserve used to restore\n")
        f.write("system frequency to nominal value after primary reserves (FCR) have responded. \n")
        f.write("Its is activated automatically based on frequency deviations and imbvalance signal . \n\n")

        f.write("The ratio of aFRR activation to total imbalance indicates:\n")
        f.write("- How much of the system imbalance is being covered by aFRR reserves\n")
        f.write("- The efficiency of the balancing market\n")
        f.write("- Whether sufficient reserves are available to cover imbalances\n\n")

        f.write("ASSESSMENT\n")
        f.write("-" * 60 + "\n")

        if avg_ratio:
            # Yüksek oran (>1.0): aFRR dengesizlikten fazla aktive oluyor
            if avg_ratio > 1.0:
                f.write("High activation ratio (>1.0): aFRR is covering more than the imbalance,\n")
                f.write("indicating possible over-activation or multiple reserve products being used.\n")
            # Orta oran (0.5-1.0): aFRR dengesizliğin önemli bir kısmını karşılıyor
            elif avg_ratio > 0.5:
                f.write("Moderate activation ratio (0.5-1.0): aFRR is actively covering a significant\n")
                f.write("portion of system imbalances, showing good reserve utilization.\n")
            # Düşük oran (<0.5): aFRR dengesizliğin yarısından azını karşılıyor
            else:
                f.write("Low activation ratio (<0.5): aFRR covers less than half of imbalances,\n")
                f.write("suggesting other balancing mechanisms or reserves are also in use.\n")
        # Oran hesaplanamadıysa (sıfır dengesizlik)
        else:
            f.write("Unable to calculate ratio due to zero imbalance values.\n")
        
        # Alt çizgi
        f.write("\n" + "=" * 60 + "\n")

    print(f"[REPORT] Generated assessment report at: {report_path}")

def main():
    """
    Ana fonksiyon - tüm işlemleri koordine eder
    """
    # Komut satırı argüman parser'ı oluştur
    parser = argparse.ArgumentParser(description="Task 1: aFRR vs Imbalance Analysis")
    # --date argümanı: hedef tarih (varsayılan: 2025-09-22)
    parser.add_argument("--date", default=TARGET_DATE, help="Target date (YYYY-MM-DD)")
    # --out argümanı: çıktı klasörü (varsayılan: outputs/task1)
    parser.add_argument("--out", default="outputs/task1", help="Output directory")
    # --timeout argümanı: HTTP timeout süresi (varsayılan: 30 saniye)
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout (seconds)")
    # Argümanları parse et (sys.argv'den otomatik okur)
    args = parser.parse_args()
    
    # Çıktı klasörünü Path objesine çevir
    output_dir = Path(args.out)
    # Klasörü oluştur (yoksa, parent klasörlerle birlikte)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Kullanıcıya bilgi ver
    print(f"[Task1] Date: {args.date}")
    print(f"[Task1] Output: {output_dir}")
    
    # Tarih aralığını API formatına çevir
    start, end = get_day_range(args.date)
    print(f"[Task1] Time window: {start} to {end}")
    
    # Veri çek
    print("\n[Task1] Fetching aFRR activation data...")
    # aFRR aktivasyon verilerini API'den çek
    afrr_data = fetch_data(REPORT_ID_AFRR, start, end, timeout=args.timeout)
    # JSON yanıtını DataFrame'e çevir
    afrr_df = parse_to_dataframe(afrr_data)
    # Kaç veri noktası geldiğini göster
    print(f"[Task1] aFRR: {len(afrr_df)} data points")
    
    print("\n[Task1] Fetching imbalance volumes data...")
    # Dengesizlik verilerini API'den çek
    imbalance_data = fetch_data(REPORT_ID_IMBALANCE, start, end, timeout=args.timeout)
    # JSON yanıtını DataFrame'e çevir
    imbalance_df = parse_to_dataframe(imbalance_data)
    # Kaç veri noktası geldiğini göster
    print(f"[Task1] Imbalance: {len(imbalance_df)} data points")
    
    # Metrikleri hesapla
    print("\n[Task1] Calculating metrics...")
    # İki DataFrame'i birleştirip metrikleri hesapla
    metrics_df = calculate_metrics(afrr_df, imbalance_df)
    # Metrikleri CSV dosyasına kaydet
    metrics_df.to_csv(output_dir / "metrics.csv")
    print(f"[Task1] Metrics saved to: {output_dir / 'metrics.csv'}")
    
    # Grafikleri oluştur
    print("\n[Task1] Creating plots...")
    # Zaman serisi ve oran grafiklerini oluştur
    create_plots(metrics_df, output_dir, args.date)
    print(f"[Task1] Plots saved to: {output_dir / 'timeseries.png'} and {output_dir / 'ratio.png'}")
    
    # Rapor oluştur
    print("\n[Task1] Generating assessment report...")
    # Değerlendirme raporunu oluştur
    generate_report(metrics_df, output_dir, args.date)
    
    # İşlem tamamlandı mesajı
    print("\n[Task1] ✓ Complete!")
    # Tüm çıktı dosyalarını listele
    print(f"[Task1] Outputs:")
    print(f"  - {output_dir / 'metrics.csv'}")
    print(f"  - {output_dir / 'timeseries.png'}")
    print(f"  - {output_dir / 'ratio.png'}")
    print(f"  - {output_dir / 'assessment.txt'}")



if __name__ == "__main__":
    main()