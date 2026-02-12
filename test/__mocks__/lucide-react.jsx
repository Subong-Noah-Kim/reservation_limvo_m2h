import * as React from "react";

function createIcon(name) {
  const Icon = (props) => React.createElement("svg", { "data-testid": `icon-${name}`, ...props });
  Icon.displayName = name;
  return Icon;
}

export const Mic = createIcon("Mic");
export const MicOff = createIcon("MicOff");
export const Activity = createIcon("Activity");
export const Music = createIcon("Music");
export const BarChart3 = createIcon("BarChart3");
export const Volume2 = createIcon("Volume2");
export const Settings = createIcon("Settings");
export const Square = createIcon("Square");
