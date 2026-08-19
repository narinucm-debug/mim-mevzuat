package com.mimmevzuat.app;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;

import java.io.IOException;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.security.KeyStore;
import java.security.cert.Certificate;
import java.security.cert.CertificateFactory;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.SSLContext;
import javax.net.ssl.TrustManagerFactory;

/**
 * MİM MEVZUAT - tamamen cihaz-içi (internetsiz) çalışan native Android
 * uygulaması. Motor (NLU + arama + kural motoru + atıf doğrulama) Chaquopy
 * ile gömülü Python olarak çalışır; hiçbir web sunucusuna/WebView'a
 * bağımlılık YOKTUR (bkz. kullanıcı talebi: "web sitesi olmasın").
 *
 * "Güncelle" butonu, PLAN.txt/UPDATE_ENGINE.txt ilkesine uygun olarak
 * yalnızca resmi kaynağa erişilebilirliği kontrol eder; hiçbir içerik
 * otomatik/sessizce indirilip devreye alınmaz (review-gated ilkesi).
 */
public class MainActivity extends Activity {

    private PyObject assistant;
    private EditText questionInput;
    private TextView answerView;
    private TextView statusView;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        setContentView(buildUi());
        statusView.setText("Mevzuat motoru yükleniyor...");

        // Python.start() dahil TÜM baslangic islemleri arka plan
        // thread'inde: bir istisna olursa uygulama SESSIZCE cokmek
        // yerine ekranda hatayi gostersin (2026-08-19: bir tablette
        // ABI uyumsuzlugu nedeniyle acilista sessiz cokme yasandi,
        // bu hatayi gorunur kilmak icin eklendi).
        new Thread(() -> {
            try {
                if (!Python.isStarted()) {
                    Python.start(new AndroidPlatform(this));
                }
                Python py = Python.getInstance();
                PyObject assistantModule = py.getModule("mim_mevzuat.assistant");
                assistant = assistantModule.callAttr("MevzuatAssistant");
                runOnUiThread(() -> statusView.setText("Hazır — internet gerekmeden çalışır."));
            } catch (Throwable t) {
                String msg = "Motor başlatılamadı: " + t;
                runOnUiThread(() -> {
                    statusView.setText("HATA — bkz. aşağı");
                    answerView.setText(msg);
                });
            }
        }).start();
    }

    private View buildUi() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(20);
        root.setPadding(pad, dp(48), pad, pad);
        root.setBackgroundColor(Color.parseColor("#0B0F19"));

        TextView title = new TextView(this);
        title.setText("MİM MEVZUAT");
        title.setTextColor(Color.parseColor("#38BDF8"));
        title.setTypeface(null, Typeface.BOLD);
        title.setTextSize(24);
        root.addView(title);

        statusView = new TextView(this);
        statusView.setTextColor(Color.parseColor("#94A3B8"));
        statusView.setTextSize(12);
        statusView.setPadding(0, dp(4), 0, dp(16));
        root.addView(statusView);

        LinearLayout row = new LinearLayout(this);
        row.setOrientation(LinearLayout.HORIZONTAL);

        questionInput = new EditText(this);
        questionInput.setHint("Mevzuata bir şey sor...");
        questionInput.setHintTextColor(Color.parseColor("#64748B"));
        questionInput.setTextColor(Color.WHITE);
        // ÖNEMLİ: EditText'in kendi varsayılan (açık renk) arka planı
        // ezilmezse metin (beyaz) görünmez oluyordu - 2026-08-19 kullanıcı
        // raporu. Arka planı da açıkça koyu yapıyoruz.
        questionInput.setBackgroundColor(Color.parseColor("#1E293B"));
        questionInput.setPadding(dp(12), dp(10), dp(12), dp(10));
        questionInput.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_FLAG_MULTI_LINE);
        LinearLayout.LayoutParams inputParams =
                new LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f);
        row.addView(questionInput, inputParams);

        Button askButton = new Button(this);
        askButton.setText("Sor");
        askButton.setOnClickListener(v -> ask());
        row.addView(askButton);

        root.addView(row);

        Button updateButton = new Button(this);
        updateButton.setText("Güncelle (internet gerekir)");
        updateButton.setOnClickListener(v -> checkForUpdates());
        LinearLayout.LayoutParams updateParams =
                new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        updateParams.topMargin = dp(8);
        root.addView(updateButton, updateParams);

        answerView = new TextView(this);
        answerView.setTextColor(Color.parseColor("#E2E8F0"));
        answerView.setTextIsSelectable(true);
        answerView.setPadding(0, dp(20), 0, 0);
        answerView.setText("Sorunuzu yukarıya yazıp \"Sor\"a basın.\n\nÖrnek: \"Kapalı otopark emsale giriyor mu?\"");

        ScrollView scroll = new ScrollView(this);
        scroll.addView(answerView);
        LinearLayout.LayoutParams scrollParams =
                new LinearLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, 0, 1f);
        root.addView(scroll, scrollParams);

        return root;
    }

    private void ask() {
        if (assistant == null) {
            Toast.makeText(this, "Motor henüz hazır değil, birkaç saniye bekleyin.", Toast.LENGTH_SHORT).show();
            return;
        }
        String q = questionInput.getText().toString().trim();
        if (q.isEmpty()) {
            return;
        }
        answerView.setText("Düşünüyorum (yerel motor, internet kullanmıyor)...");

        new Thread(() -> {
            try {
                String formatted = assistant.callAttr("ask_formatted", q).toString();
                runOnUiThread(() -> answerView.setText(formatted));
            } catch (Exception e) {
                String msg = "Hata: " + e.getMessage();
                runOnUiThread(() -> answerView.setText(msg));
            }
        }).start();
    }

    private void checkForUpdates() {
        statusView.setText("Bağlantı kontrol ediliyor...");
        new Thread(() -> {
            boolean reachable = isMevzuatGovTrReachable();
            runOnUiThread(() -> {
                if (reachable) {
                    statusView.setText("İnternet bağlantısı var — mevzuat.gov.tr erişilebilir.");
                    Toast.makeText(
                            this,
                            "Resmi kaynağa ulaşıldı. Bu sürümde otomatik içerik güncellemesi "
                                    + "henüz uygulanmıyor (bkz. UPDATE_ENGINE.txt: değişiklikler "
                                    + "önce incelenip onaylanmadan devreye alınmaz). En güncel resmi "
                                    + "metin için mevzuat.gov.tr'yi ziyaret edebilirsiniz.",
                            Toast.LENGTH_LONG
                    ).show();
                } else {
                    statusView.setText("Hazır — internet gerekmeden çalışır.");
                    Toast.makeText(
                            this,
                            "İnternet bağlantısı bulunamadı. Uygulama zaten internetsiz "
                                    + "çalışacak şekilde tasarlandı, bu ekran yalnızca güncellik "
                                    + "kontrolü içindir.",
                            Toast.LENGTH_LONG
                    ).show();
                }
            });
        }).start();
    }

    /** mevzuat.gov.tr'ye gerçek bir HTTP isteğiyle erişilebilirlik kontrolü.
     * İKİ ayrı düzeltme gerekiyor - ikisi de SOURCE_MAP.txt "Doğrulama
     * Notu"nda (Python/http_client.py için) belgelenen kök nedenlerin
     * Android/Java tarafındaki karşılığı:
     *  1. Tarayıcı benzeri User-Agent (yoksa istek sessizce düşüyor).
     *  2. mevzuat.gov.tr TLS el sıkışmasında ara sertifikayı (GeoTrust
     *     TLS RSA CA G1) göndermiyor - Android'in varsayılan güven
     *     deposu bunu otomatik tamamlamıyor, bu yüzden SSLHandshakeException
     *     alınıyordu (IOException'ın alt sınıfı olduğu için sessizce
     *     "bağlantı yok" gibi yorumlanıyordu - "Güncelle çalışmıyor"
     *     şikayetinin gerçek nedeni buydu). assets/geotrust_tls_rsa_ca_g1.pem
     *     güven deposuna eklenerek çözülüyor - verify=False YOLUNA
     *     GİDİLMEDİ, sertifika doğrulaması tam olarak çalışmaya devam
     *     ediyor. */
    private boolean isMevzuatGovTrReachable() {
        try {
            URL url = new URL("https://www.mevzuat.gov.tr/");
            HttpsURLConnection conn = (HttpsURLConnection) url.openConnection();
            conn.setSSLSocketFactory(buildMevzuatGovTrSslContext().getSocketFactory());
            conn.setRequestProperty(
                    "User-Agent",
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                            + "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            );
            conn.setConnectTimeout(8000);
            conn.setReadTimeout(8000);
            int code = conn.getResponseCode();
            conn.disconnect();
            return code >= 200 && code < 400;
        } catch (Exception e) {
            return false;
        }
    }

    /** Sistemin varsayılan güvenilir sertifikalarına, mevzuat.gov.tr'nin
     * eksik gönderdiği ara sertifikayı EKLEYEN bir SSLContext döner. */
    private SSLContext buildMevzuatGovTrSslContext() throws Exception {
        CertificateFactory cf = CertificateFactory.getInstance("X.509");
        Certificate extraCa;
        try (InputStream in = getAssets().open("geotrust_tls_rsa_ca_g1.pem")) {
            extraCa = cf.generateCertificate(in);
        }

        // Sistemin varsayılan güvenilir CA'larını yükle (AndroidCAStore)
        KeyStore systemStore = KeyStore.getInstance("AndroidCAStore");
        systemStore.load(null, null);

        // Ayrı bir KeyStore'a hem sistem CA'larını hem de eksik ara
        // sertifikayı koy - böylece diğer HTTPS sitelerine güven ZARAR
        // GÖRMEZ, yalnızca bu bağlantı için ek bir güven çıpası eklenir.
        KeyStore combined = KeyStore.getInstance(KeyStore.getDefaultType());
        combined.load(null, null);
        int i = 0;
        java.util.Enumeration<String> aliases = systemStore.aliases();
        while (aliases.hasMoreElements()) {
            String alias = aliases.nextElement();
            combined.setCertificateEntry(alias, systemStore.getCertificate(alias));
        }
        combined.setCertificateEntry("mevzuat-gov-tr-intermediate", extraCa);

        TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
        tmf.init(combined);

        SSLContext context = SSLContext.getInstance("TLS");
        context.init(null, tmf.getTrustManagers(), null);
        return context;
    }

    private int dp(int value) {
        float density = getResources().getDisplayMetrics().density;
        return Math.round(value * density);
    }
}
