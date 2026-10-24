import { createContext, useContext, useState, type ReactNode } from 'react'

// English / Bahasa Malaysia for navigation, onboarding, page titles and main actions. Texts are
// keyed by their English wording; anything without a translation stays in English. Evidence,
// source passages and numbers are never translated. Translated by the team with AI assistance;
// a native-speaker review is still pending, and the app says so.
export type Lang = 'en' | 'ms'
const KEY = 'qart.lang'

const MS: Record<string, string> = {
  // navigation
  'Your journey · GBS finance': 'Perjalanan anda · kewangan GBS',
  'Also useful': 'Turut berguna',
  Overview: 'Gambaran keseluruhan',
  'My goal': 'Matlamat saya',
  'My options': 'Pilihan saya',
  'My plan': 'Pelan saya',
  'Today → Future you': 'Hari ini → Anda pada masa depan',
  'What changed': 'Apa yang berubah',
  'My CV': 'CV saya',
  Evidence: 'Bukti',
  Trends: 'Trend',
  'Any occupation': 'Mana-mana pekerjaan',
  'Live intelligence': 'Risikan langsung',
  'Start again with a new profile': 'Mula semula dengan profil baharu',
  'Start · tell us about yourself': 'Mula · ceritakan tentang diri anda',
  // onboarding
  'Your situation': 'Situasi anda',
  'Your CV': 'CV anda',
  'Your work today': 'Kerja anda hari ini',
  'Your skills': 'Kemahiran anda',
  'Time and budget': 'Masa dan bajet',
  'What matters to you': 'Perkara penting bagi anda',
  'I work in finance now': 'Saya bekerja dalam bidang kewangan sekarang',
  'See how AI is changing your tasks, and routes to nearby roles.': 'Lihat bagaimana AI mengubah tugas anda, dan laluan ke peranan berdekatan.',
  "I'm studying or just graduated": 'Saya sedang belajar atau baru tamat pengajian',
  'Entry roles that fit you and the skills to build first.': 'Peranan permulaan yang sesuai dengan anda dan kemahiran untuk dibina dahulu.',
  'I want to move into finance': 'Saya mahu beralih ke bidang kewangan',
  'Which of your skills carry over, and a plan to switch.': 'Kemahiran anda yang boleh dibawa, dan pelan untuk beralih.',
  'Working with data and systems': 'Bekerja dengan data dan sistem',
  'Accounting and finance work': 'Kerja perakaunan dan kewangan',
  'Sustainability (ESG)': 'Kelestarian (ESG)',
  'Improving processes and working with people': 'Menambah baik proses dan bekerja dengan orang',
  'Skip to the evidence overview': 'Langkau ke gambaran bukti',
  'GBS finance & accounting · Malaysia': 'Kewangan & perakaunan GBS · Malaysia',
  'Where is your finance career going as AI changes the work?': 'Ke manakah hala tuju kerjaya kewangan anda apabila AI mengubah kerja?',
  'Start · about 3 minutes': 'Mula · kira-kira 3 minit',
  'Skip any question. The demo uses synthetic CVs only.': 'Langkau mana-mana soalan. Demo ini menggunakan CV sintetik sahaja.',
  'Which describes you?': 'Yang manakah menggambarkan anda?',
  'This changes what you see first.': 'Ini mengubah apa yang anda lihat dahulu.',
  'Add your CV': 'Tambah CV anda',
  'We pre-fill the next questions from it. Prefer not to? Skip and answer them yourself.': 'Kami mengisi soalan seterusnya daripadanya. Tidak mahu? Langkau dan jawab sendiri.',
  'Drop a PDF, DOCX or text file': 'Letakkan fail PDF, DOCX atau teks',
  'Or try a synthetic sample': 'Atau cuba contoh sintetik',
  'Names, IC numbers, phone numbers and emails are removed before anything reads the CV. The CV text itself is not stored.': 'Nama, nombor IC, nombor telefon dan e-mel dibuang sebelum CV dibaca. Teks CV itu sendiri tidak disimpan.',
  'What have you studied and done?': 'Apakah yang telah anda pelajari dan lakukan?',
  'What do you do today?': 'Apakah kerja anda hari ini?',
  'None of these': 'Tiada antara ini',
  'Check your skills': 'Semak kemahiran anda',
  'No skills yet. Add the ones you have below.': 'Belum ada kemahiran. Tambah kemahiran yang anda ada di bawah.',
  'How much time and money can you put into learning?': 'Berapa banyak masa dan wang yang boleh anda peruntukkan untuk belajar?',
  'Hours per week': 'Jam seminggu',
  Budget: 'Bajet',
  'Free only': 'Percuma sahaja',
  'Free + HRD Corp-claimable': 'Percuma + boleh dituntut HRD Corp',
  'Up to RM 500': 'Sehingga RM 500',
  'Every course listed today is free. HRD Corp-claimable programmes are shown only once the official listing confirms them.': 'Semua kursus yang disenaraikan hari ini adalah percuma. Program yang boleh dituntut HRD Corp hanya ditunjukkan selepas senarai rasmi mengesahkannya.',
  'What matters to you in your next role?': 'Apakah yang penting bagi anda dalam peranan seterusnya?',
  'Used only to order roles that fit you almost equally well. It never changes a fit score.': 'Digunakan hanya untuk menyusun peranan yang hampir sama padan dengan anda. Ia tidak pernah mengubah skor padanan.',
  'Sustainable Development Goals you care about (optional)': 'Matlamat Pembangunan Mampan yang penting bagi anda (pilihan)',
  Ready: 'Sedia',
  'Almost there': 'Hampir siap',
  "Building your picture from today's evidence": 'Membina gambaran anda daripada bukti hari ini',
  'See roles that fit me →': 'Lihat peranan yang sesuai dengan saya →',
  'Or look at the evidence first': 'Atau lihat bukti dahulu',
  Skip: 'Langkau',
  'Build my picture': 'Bina gambaran saya',
  Continue: 'Teruskan',
  'Reading the sample CV…': 'Membaca CV contoh…',
  'Reading your CV…': 'Membaca CV anda…',
  'Matching your tasks to skills…': 'Memadankan tugas anda dengan kemahiran…',
  'Building your picture…': 'Membina gambaran anda…',
  // page titles and main actions
  'What the evidence shows for your field': 'Apa yang ditunjukkan oleh bukti untuk bidang anda',
  'Where your skills can take you': 'Ke mana kemahiran anda boleh membawa anda',
  'Where do you want to be?': 'Di manakah anda mahu berada?',
  'What is growing, what is shrinking': 'Apa yang berkembang, apa yang mengecil',
  'What the evidence says about your job': 'Apa kata bukti tentang pekerjaan anda',
  'Your CV, updated from what you confirmed': 'CV anda, dikemas kini daripada apa yang anda sahkan',
  'See the difference, then choose': 'Lihat perbezaannya, kemudian pilih',
  'Where every number comes from': 'Dari mana setiap angka datang',
  'Choose as my destination': 'Pilih sebagai destinasi saya',
  'Save my goal': 'Simpan matlamat saya',
  'Find my occupation': 'Cari pekerjaan saya',
  'Explain this in plain words': 'Terangkan dengan bahasa mudah',
  'Mark as done': 'Tandakan selesai',
  'Open course ↗': 'Buka kursus ↗',
  'Pause for now': 'Jeda dahulu',
  Resume: 'Sambung',
  'Report a problem': 'Laporkan masalah',
  Send: 'Hantar',
  'Download as text': 'Muat turun sebagai teks',
}

type Ctx = { lang: Lang; setLang: (l: Lang) => void; t: (text: string) => string }
const LangContext = createContext<Ctx>({ lang: 'en', setLang: () => {}, t: (s) => s })

function stored(): Lang {
  try {
    return window.localStorage.getItem(KEY) === 'ms' ? 'ms' : 'en'
  } catch {
    return 'en'
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  const [lang, set] = useState<Lang>(stored)
  const setLang = (l: Lang) => {
    set(l)
    document.documentElement.lang = l === 'ms' ? 'ms' : 'en'
    try {
      window.localStorage.setItem(KEY, l)
    } catch {
      // Not remembered across visits; the choice still applies now.
    }
  }
  const t = (text: string) => (lang === 'ms' ? (MS[text] ?? text) : text)
  return <LangContext.Provider value={{ lang, setLang, t }}>{children}</LangContext.Provider>
}

export function useT() {
  return useContext(LangContext)
}

export function LanguageSwitch() {
  const { lang, setLang } = useT()
  return (
    <div className="flex flex-col gap-1 px-2.5">
      <div className="flex gap-1" role="group" aria-label="Language / Bahasa">
        {(['en', 'ms'] as Lang[]).map((l) => (
          <button key={l} type="button" aria-pressed={lang === l} onClick={() => setLang(l)} className={`cursor-pointer rounded-md border-0 px-2.5 py-1 text-xs ${lang === l ? 'bg-violet text-white' : 'bg-surface text-stone'}`}>
            {l === 'en' ? 'English' : 'Bahasa Malaysia'}
          </button>
        ))}
      </div>
      {lang === 'ms' && (
        <span className="text-[10px] leading-tight text-slate-mid">
          BM: navigasi, pendaftaran, tajuk dan butang utama. Bukti kekal dalam bahasa asal. Diterjemah oleh pasukan dengan bantuan AI; semakan penutur asli belum dibuat.
        </span>
      )}
    </div>
  )
}
