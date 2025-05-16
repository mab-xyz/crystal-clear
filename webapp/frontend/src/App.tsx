import "./App.css";
import Graph from "./pages/graph/Graph";
import { styleReset } from 'react95';
import { createGlobalStyle, ThemeProvider } from 'styled-components';
import { LocalAlertProvider } from "@/components/ui/local-alert";



/* Pick a theme of your choice */
// import original from 'react95/dist/themes/original';
// import cherry from 'react95/dist/themes/cherry';
import blackAndWhite from 'react95/dist/themes/blackAndWhite';

/* Original Windows95 font (optional) */
import ms_sans_serif from 'react95/dist/fonts/ms_sans_serif.woff2';
import ms_sans_serif_bold from 'react95/dist/fonts/ms_sans_serif_bold.woff2';

const GlobalStyles = createGlobalStyle`
  ${styleReset}
  @font-face {
    font-family: 'ms_sans_serif';
    src: url('${ms_sans_serif}') format('woff2');
    font-weight: 400;
    font-style: normal
  }
  @font-face {
    font-family: 'ms_sans_serif';
    src: url('${ms_sans_serif_bold}') format('woff2');
    font-weight: bold;
    font-style: normal
  }
  body, input, select, textarea {
    font-family: 'Funnel Sans';
  }
`;

const App = () => (
  <div>
    <GlobalStyles />
    <LocalAlertProvider>
      <ThemeProvider theme={blackAndWhite}>
        <Graph />
      </ThemeProvider>
    </LocalAlertProvider>
  </div>
);

export default App;