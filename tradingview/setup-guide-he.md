# מדריך התקנה: אינדיקטור Elliott/Fib ב-TradingView ושליחת התראות ל-relay

האינדיקטור `elliott_fib_pit.pine` מחשב את רמות הפיבו, את ספירת האליוט ואת סטופ המבנה באותה דרך שהסורק מחשב אותם. ההתראות שלו נרשמות **רק כעמודה ניסיונית** (דעה שנייה). הן לא משנות את הסטופים הפעילים של הסורק.

> שמות הכפתורים מופיעים באנגלית כמו בממשק של TradingView. ליד כל שלב יש קישור לתיעוד הרשמי, למקרה שהממשק השתנה.

## מה צריך לפני שמתחילים
1. **מנוי בתשלום ב-TradingView.** התראות Webhook זמינות רק בתוכניות בתשלום (ראו "Webhook notifications" בטבלת התוכניות): https://www.tradingview.com/pricing/
2. **אימות דו-שלבי (2FA) פעיל בחשבון.** בלי זה TradingView לא מאפשר Webhook:
   https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/
   הוראות להפעלה (Profile ← "Privacy and Security" ← Account Settings): https://www.tradingview.com/support/solutions/43000572460-how-to-configure-2fa/
3. **כתובת ה-RELAY:** `https://scanner-tv-relay.vercel.app/api/tv`. זה פרויקט Vercel נפרד בשם scanner-tv-relay, שמקבל רק POST עם JSON. TradingView מקבל רק כתובות בפורט 80 או 443 (כלומר `https://...` רגיל בלי פורט אחר). הוא לא תומך ב-IPv6, ומבטל בקשה אם השרת לא עונה תוך 3 שניות (אותו קישור של Webhook למעלה).

## שלב 1: הדבקת הסקריפט והוספה לגרף
1. פתחו גרף ב-TradingView ופתחו את ה-Pine Editor (אייקון "Pine" בסרגל הימני):
   https://www.tradingview.com/support/solutions/43000763320-how-to-work-with-pine-editor/
2. בתפריט שליד שם הסקריפט בחרו "Create new" ← "Indicator", סמנו את כל הקוד שבעורך והחליפו אותו בכל התוכן של `elliott_fib_pit.pine`.
3. שמרו (Ctrl+S) ותנו שם, למשל `EF-PIT`.
4. לחצו "Add to chart".
   (השלבים 2–4 לפי המדריך הרשמי: https://www.tradingview.com/pine-script-docs/primer/first-indicator/)
5. עבדו על **גרף יומי** (1D), כי הסורק מחושב על נרות יומיים.

## שלב 2: מילוי ה-secret ושאר ההגדרות
1. לחצו על כפתור ה-Settings שליד שם האינדיקטור על הגרף:
   https://www.tradingview.com/support/solutions/43000480333-how-to-adjust-the-indicator-settings/
2. בקבוצה "Alert / relay" מלאו בשדה **secret** את הסיסמה המשותפת של ה-relay. ה-relay בודק אותה, כי TradingView לא יכול לשלוח כותרת Authorization.
   **מאיפה מקבלים אותה:** זו מחרוזת אקראית של 64 תווים שנוצרה כשהוקם ה-relay. היא שמורה רק כמשתנה סודי בפרויקט ב-Vercel ובקובץ מוגן במחשב של הבוט. היא **לא** כתובה במדריך הזה ולא תישלח בצ'אט הקבוצתי. שוק ההון ימסור לך אותה בצורה מאובטחת בצ'אט הפרטי, ואתה תדביק אותה ישירות בשדה. אם ה-secret שגוי, ה-relay דוחה את ההתראה (שגיאה 401), וביומן ההתראות של TradingView יופיע כשל ב-Webhook status.
3. **Direction:** ‏Long לסטאפ לונג, ‏Short לסטאפ שורט.
4. **לא לשנות** את ATR length ‏(14) ואת Zigzag reversal ‏(2.0). אלה ערכי הסורק.
5. **Reference stop (רשות):** אם יש עסקה פתוחה, הזינו Entry date בפורמט `YYYY-MM-DD` ו-Entry price. במצב "Auto" הקו מציג את הכלל הפעיל: במניות סטופ נגרר של 4×ATR על שערי סגירה, בלונג קריפטו סטופ קבוע של 3×ATR, ובשורט קריפטו אין קו (מוקפא).
6. **מניות:** כדי שהמחירים יתאימו לסורק (Yahoo מתואם לדיבידנדים), הפעילו בהגדרות הגרף את "Adjust data for dividends":
   https://www.tradingview.com/support/solutions/43000590597-how-to-adjust-data-for-dividends/
7. **קריפטו:** הנתונים משתנים מבורסה לבורסה. ראו את ההערה בסוף המדריך.

## שלב 3: יצירת ההתראה
1. פתחו את חלון יצירת ההתראה, למשל עם הכפתור בסרגל העליון או עם ALT+A (‏⌥+A במק):
   https://www.tradingview.com/support/solutions/43000595315-how-to-set-up-alerts/
2. בשדה **Condition** בחרו את האינדיקטור `EF-PIT`, ואז את האפשרות **"Any alert() function call"**:
   https://www.tradingview.com/support/solutions/43000597494-alerts-on-alert-function/
3. **תדירות:** אם מופיעה בחירת תדירות, בחרו **"Once Per Bar Close"**. גם בלי זה, הסקריפט עצמו שולח רק בסגירת נר (`alert.freq_once_per_bar_close`). לפי TradingView, בהתראות מסוג alert() הקוד קובע את התדירות ואת תוכן ההודעה, לא חלון ההתראה (אותו קישור).
4. את תוכן ההודעה אין צורך לכתוב. הסקריפט שולח JSON מוכן עם השדות: ticker, exchange, timeframe, signal, close, bar_time, wave_label, fib_0382 … fib_2618, struct_stop, elliott_target_w3/w5, secret.

## שלב 4: חיבור ל-Webhook
1. באפשרויות ההתראה (Alert actions / Notifications) סמנו **"Webhook URL"**:
   https://www.tradingview.com/support/solutions/43000595315-how-to-set-up-alerts/
2. הדביקו את **כתובת ה-RELAY**: `https://scanner-tv-relay.vercel.app/api/tv`
3. צרו את ההתראה (Create).
4. בדיקה: ביומן ההתראות יש עמודה בשם "Webhook status" שמראה אם ההודעה הגיעה:
   https://www.tradingview.com/support/solutions/43000529348-how-to-configure-webhook-alerts/

## חשוב לדעת
- **התראה אחת לכל מניה.** התראה נשמרת עם הסימול, עם הטיימפריים ועם ההגדרות שהיו בגרף כשיצרתם אותה. אם משנים אחר כך הגדרה, למשל את ה-secret או את ה-Direction, צריך למחוק את ההתראה וליצור חדשה:
  https://www.tradingview.com/pine-script-docs/concepts/alerts/
- **מגבלות לפי תוכנית.** התראה על סקריפט נחשבת "Technical alert". מספר ההתראות הפעילות מוגבל לפי התוכנית, ובחלק מהתוכניות להתראות יש גם תוקף שפג. המספרים המעודכנים נמצאים בטבלת המחירים:
  https://www.tradingview.com/pricing/ ‏· https://www.tradingview.com/support/solutions/43000696403-alerts-separation-by-type/
- **עצירה אוטומטית.** TradingView עוצר התראת סקריפט שנשלחה יותר מ-15 פעמים בתוך 3 דקות (בפועל זה לא צפוי כאן, כי ההתראה נשלחת לכל היותר פעם אחת בסגירת נר יומי). מקור: https://www.tradingview.com/support/solutions/43000597494-alerts-on-alert-function/
- **אבטחה.** TradingView ממליץ לא לשלוח סיסמאות בגוף ה-Webhook. ה-secret כאן הוא מפתח ייעודי ל-relay בלבד. אל תשתמשו בסיסמה של אף חשבון, ואפשר להחליף אותו בכל רגע.
- **אין צביעה מחדש.** כל החישובים נעשים רק על נרות סגורים. על הנר הפתוח מוצגים הערכים של הנר הסגור האחרון. קו הזיגזג לפיבוט מצויר רק ביום שבו הפיבוט אושר.
- **קריפטו (BTC):** הסורק משתמש בנתוני BTC-USD של Yahoo. נרות יומיים של בורסה ספציפית שונים קצת. בבדיקה על נרות Coinbase, ההבדל הזה הספיק כדי לאשר פיבוט נוסף ולשנות את ספירת הגלים. לכן ההתראות על קריפטו הן דעה שנייה גסה יותר מאשר במניות.
