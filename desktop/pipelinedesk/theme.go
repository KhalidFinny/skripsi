package main

import "github.com/egoist/mygo/ui"

var (
	aquaSky     = ui.Hex("#DDF8FF")
	aquaBorder  = ui.RGBA(58, 157, 214, 0.62)
	aquaInk     = ui.Hex("#073875")
	aquaMuted   = ui.Hex("#2E6FA3")
	aquaBlue    = ui.Hex("#0D67C6")
	aquaGreen   = ui.Hex("#74EC65")
	aquaGreenHi = ui.Hex("#B7FF9A")
	aquaGreenLo = ui.Hex("#2CCF67")
	aquaRed     = ui.Hex("#FF4B59")
	aquaCoral   = ui.Hex("#FF8A92")
)

func aquaTheme() *ui.Theme {
	return &ui.Theme{
		Background:     aquaSky,
		Surface:        ui.RGBA(235, 250, 255, 0.86),
		SurfaceHover:   ui.RGBA(220, 245, 255, 0.94),
		SurfacePressed: ui.RGBA(188, 231, 247, 0.96),
		Border:         aquaBorder,
		Text:           aquaInk,
		TextMuted:      aquaMuted,
		Accent:         aquaGreen,
		AccentHover:    aquaGreenHi,
		AccentPressed:  aquaGreenLo,
		AccentText:     ui.Hex("#032A12"),
		Danger:         aquaRed,
		Warning:        ui.Hex("#F3A51A"),
		Success:        aquaGreenLo,
		Selection:      ui.RGBA(13, 103, 198, 0.25),
		Focus:          ui.RGBA(13, 103, 198, 0.62),
		Inverse:        ui.Hex("#06305E"),
		InverseText:    ui.Hex("#F2FCFF"),
		Scrollbar:      ui.RGBA(13, 103, 198, 0.42),
		ScrollbarWidth: 8,
		Radius:         18,
		Spacing:        4,
		FontSize:       14,
	}
}
