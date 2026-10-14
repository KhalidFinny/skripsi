package main

import (
	"log"

	"github.com/egoist/mygo"
	"github.com/egoist/mygo/ui"
)

func main() {
	a := newApp()
	mygo.App.WhenReady(func() {
		a.win = mygo.NewWindow(mygo.WindowOptions{
			Title:           "Pipeline Desk",
			Width:           1440,
			Height:          900,
			MinWidth:        1120,
			MinHeight:       720,
			TitleBarStyle:   mygo.TitleBarHidden,
			BackgroundColor: "#DDF8FF",
			StateKey:        "main",
			Content:         ui.View(a.view),
		})
	})
	if err := mygo.App.Run(); err != nil {
		log.Fatal(err)
	}
}
