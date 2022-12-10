import {
  Streamlit,
  StreamlitComponentBase,
  withStreamlitConnection,
} from "streamlit-component-lib"
import React from "react"
import Graph from 'react-graph-vis';

const options = {
  nodes:{
    font:{
      color: "#000000",
      strokeWidth: 2,
      strokeColor: "#FFFFFF"
    }
  }
};

interface State{
  graph: any,
  events: any,
  options: any,
  width: any
}

class StreamlitVisGraph extends StreamlitComponentBase<State> {
  public state = {
    graph: JSON.parse(this.props.args["data"]),
    events: {
      select: (event: any) => {
        console.log("Selected nodes:");
        console.log(event.nodes[0]);
        Streamlit.setComponentValue(event.nodes[0])
      },
      // doubleClick: ({ pointer: { canvas } }) => {
      //   createNode(canvas.x, canvas.y);
      // }
    },
    options: {...JSON.parse(this.props.args["options"]), ...options},
    width: this.props.width
  }
  
  render = () => {
    return (
      <Graph
      graph={this.state.graph}
      options={this.state.options}
      events={this.state.events}
      style={{height: "900px", width: this.state.width}}
      />
    );
  }
}

export default withStreamlitConnection(StreamlitVisGraph)