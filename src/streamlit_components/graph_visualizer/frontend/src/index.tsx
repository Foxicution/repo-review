import React from "react"
import ReactDOM from "react-dom"
import MyComponent from "./MyComponent"
import { StreamlitProvider } from "streamlit-component-lib-react-hooks"

ReactDOM.render(
  <React.StrictMode>
    <StreamlitProvider>
    <div style={{ height: 800, width: "100%" }}>
      <MyComponent />
    </div>
    </StreamlitProvider>
  </React.StrictMode>,
  document.getElementById("root")
)
