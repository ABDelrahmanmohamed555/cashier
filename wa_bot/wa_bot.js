// wa_bot.js — إرسال رسائل/ملفات واتساب بدون فتح واتس ويب (جلسة محلية في wa_bot/session)
// الأول مرة فقط: node wa_bot.js pair   -> امسح الـ QR بالموبايل (بيتخزن بعدها للأبد)
// بعدين:        node wa_bot.js send <رقم_بالكود_الدولي> <ملف> [نص]
//               node wa_bot.js send <رقم> <ملف> --caption "نص"
const path = require("path");
const { Client, LocalAuth, MessageMedia } = require("whatsapp-web.js");

const SESSION_DIR = path.join(__dirname, "session");
const PUPPETEER_OPTIONS = {
  headless: true, // من غير نافذة نهائيًا
  executablePath: "/usr/bin/chromium",
  args: [
    "--no-sandbox",
    "--disable-gpu",
    "--disable-dev-shm-usage",
    "--disable-setuid-sandbox",
    "--no-first-run",
    "--no-zygote",
    "--single-process",
  ],
};

function makeClient(printQr) {
  const client = new Client({
    authStrategy: new LocalAuth({ dataPath: SESSION_DIR }),
    puppeteer: PUPPETEER_OPTIONS,
    qrMaxRetries: 3,
  });
  if (printQr) {
    client.on("qr", (qr) => {
      const qrcode = require("qrcode-terminal");
      console.log("=== امسح الـ QR ده بالتليفون (مرة واحدة بس) ===");
      qrcode.generate(qr, { small: true });
    });
  }
  client.on("authenticated", () => console.log("الجلسة اتأكدت ✓"));
  client.on("auth_failure", (msg) => {
    console.error("فشل الدخول للجلسة (امسح session/ وارجع اعمل pair):", msg);
    process.exit(1);
  });
  client.on("ready", () => console.log("WhatsApp جاهز (headless) ✓"));
  client.on("disconnected", (reason) => console.log("اتفصل:", reason));
  return client;
}

function normalizeNumber(num) {
  let n = String(num).replace(/\D/g, "");
  if (n.startsWith("0")) n = "20" + n; // أرقام مصرية 01x -> +20
  if (!n.startsWith("20")) n = "20" + n;
  return n + "@c.us";
}

async function cmdPair() {
  const client = makeClient(true);
  await client.initialize();
  await new Promise((res) => client.on("ready", res));
  console.log("الاقتران تم بنجاح — الجلسة محفوظة في", SESSION_DIR);
  process.exit(0);
}

async function cmdSend(number, file, caption) {
  const client = makeClient(false);
  console.log("جارٍ تشغيل واتس (headless) ...");
  await client.initialize();
  if (!client.info || !client.info.wid) {
    console.error("الجلسة مش مقترنة بالتليفون بعد. أول مرة بس:");
    console.error("  cd " + __dirname + " && node wa_bot.js pair");
    console.error("بعد ما تمسح الـ QR بالتليفون، هتبقي تبعتي مباشرة من غير أي نافذة.");
    process.exit(3);
  }
  console.log(`متصل كـ ${client.info.pushname}`);
  const media = MessageMedia.fromFilePath(file);
  const target = normalizeNumber(number);
  console.log("بعتي لـ", target, "...");
  await client.sendMessage(target, media, caption ? { caption } : {});
  console.log("اترسلت ✓");
  process.exit(0);
}

const [cmd, ...rest] = process.argv.slice(2);
// send <رقم> <ملف> [--caption "نص"]
if (cmd === "pair") {
  cmdPair().catch((e) => {
    console.error("خطأ:", e.message);
    process.exit(1);
  });
} else if (cmd === "send") {
  const cc = rest.indexOf("--caption");
  let caption = "";
  let args = rest;
  if (cc !== -1) {
    caption = rest[cc + 1] || "";
    args = rest.slice(0, cc);
  }
  const [number, file] = args;
  if (!number || !file) {
    console.error("الاستخدام: node wa_bot.js send <رقم> <ملف> [--caption نص]");
    process.exit(2);
  }
  cmdSend(number, file, caption).catch((e) => {
    console.error("خطأ:", e.message);
    process.exit(1);
  });
} else {
  console.error("استخدام:\n  node wa_bot.js pair [مسح QR أول مرة]\n  node wa_bot.js send <رقم> <ملف> [--caption نص]");
  process.exit(2);
}