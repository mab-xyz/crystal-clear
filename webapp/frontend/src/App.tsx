import "./App.css";
import Graph from "./pages/graph/Graph";
import { styleReset } from 'react95';
import { createGlobalStyle } from 'styled-components';
import { LocalAlertProvider } from "@/components/ui/local-alert";
import Home from "./pages/homepage/Home";
import { Routes, Route } from "react-router";
import ContractGraph from "./pages/graph/Graph";
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
  @font-face {
    font-family: 'Jersey 20';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('./assets/Jersey20.woff2') format('woff2');
    unicode-range: U+0100-02BA, U+02BD-02C5, U+02C7-02CC, U+02CE-02D7, U+02DD-02FF, U+0304, U+0308, U+0329, U+1D00-1DBF, U+1E00-1E9F, U+1EF2-1EFF, U+2020, U+20A0-20AB, U+20AD-20C0, U+2113, U+2C60-2C7F, U+A720-A7FF;
  }
`;

const App = () => (
  <div>
    <GlobalStyles />
    <LocalAlertProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/graph" element={<Graph />} />
        <Route path="/graph/:address" element={<ContractGraph />} />
      </Routes>
    </LocalAlertProvider>
  </div>
);

export default App;