// Tokens: the pale-green noting sheet of a government file, blue-black ink, and the violet of stamp-pad ink.
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Mukta', 'system-ui', 'sans-serif'],
        file: ['"Tiro Devanagari Hindi"', 'Georgia', 'serif'],
      },
      colors: {
        sheet: '#E9F0E7',           // noting-sheet green: the page
        paper: '#FBFCFA',           // enclosures and ledgers
        rule: '#C7D3C4',            // ruled lines
        ink: { DEFAULT: '#1C2B3A', soft: '#4B5B69', faint: '#7A8894' },
        stamp: { DEFAULT: '#4E3A8E', soft: '#EDE8F7', deep: '#382868' },
        red: { ink: '#A4262C', soft: '#F7E6E6' },          // money paid wrongly
        ochre: { DEFAULT: '#9A5B00', soft: '#F6ECD9' },    // people left out
      },
      borderRadius: { file: '6px' },
    },
  },
  plugins: [],
}
