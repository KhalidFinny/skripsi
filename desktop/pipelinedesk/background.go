package main

import (
	"image"
	"image/color"
	"math"
	"sync"

	"github.com/egoist/mygo/ui"
)

var frutigerBackground struct {
	sync.Once
	bitmap *ui.Bitmap
}

func frutigerAeroBackground() *ui.Bitmap {
	frutigerBackground.Do(func() {
		frutigerBackground.bitmap = ui.NewBitmap(drawFrutigerAeroBackground(1600, 1000))
	})
	return frutigerBackground.bitmap
}

func drawFrutigerAeroBackground(w, h int) image.Image {
	img := image.NewRGBA(image.Rect(0, 0, w, h))
	for y := 0; y < h; y++ {
		t := float64(y) / float64(h)
		c := mix(color.RGBA{R: 236, G: 250, B: 255, A: 255}, color.RGBA{R: 147, G: 207, B: 236, A: 255}, t)
		for x := 0; x < w; x++ {
			img.SetRGBA(x, y, c)
		}
	}

	// Soft sun bloom and Aero streaks, kept low-contrast so panels stay readable.
	drawRadial(img, int(float64(w)*0.76), int(float64(h)*0.18), 420, color.RGBA{R: 255, G: 255, B: 255, A: 86})
	drawRibbon(img, float64(w)*0.02, float64(h)*0.28, float64(w)*0.9, float64(h)*0.48, 26, color.RGBA{R: 255, G: 255, B: 255, A: 38})
	drawRibbon(img, float64(w)*0.18, float64(h)*0.18, float64(w)*0.95, float64(h)*0.34, 18, color.RGBA{R: 123, G: 202, B: 231, A: 32})

	// Frutiger green horizon, mostly below content.
	drawHill(img, float64(h)*0.83, float64(h)*0.10, color.RGBA{R: 159, G: 222, B: 101, A: 190})
	drawHill(img, float64(h)*0.91, float64(h)*0.07, color.RGBA{R: 93, G: 186, B: 92, A: 180})

	for _, b := range []struct {
		x, y, r int
		a       uint8
	}{
		{x: 150, y: 690, r: 72, a: 64},
		{x: 1310, y: 165, r: 88, a: 50},
		{x: 1430, y: 740, r: 54, a: 46},
	} {
		drawBubble(img, b.x, b.y, b.r, b.a)
	}
	return img
}

func drawHill(img *image.RGBA, baseY, amplitude float64, c color.RGBA) {
	b := img.Bounds()
	for x := b.Min.X; x < b.Max.X; x++ {
		n := math.Sin(float64(x)*0.005)*amplitude + math.Sin(float64(x)*0.0017+1.4)*amplitude*0.6
		y0 := int(baseY + n)
		for y := y0; y < b.Max.Y; y++ {
			blendAt(img, x, y, c)
		}
	}
}

func drawRadial(img *image.RGBA, cx, cy, radius int, c color.RGBA) {
	r2 := float64(radius * radius)
	for y := cy - radius; y <= cy+radius; y++ {
		for x := cx - radius; x <= cx+radius; x++ {
			dx, dy := float64(x-cx), float64(y-cy)
			d2 := dx*dx + dy*dy
			if d2 > r2 {
				continue
			}
			a := c.A
			c.A = uint8(float64(a) * math.Pow(1-d2/r2, 1.8))
			blendAt(img, x, y, c)
			c.A = a
		}
	}
}

func drawBubble(img *image.RGBA, cx, cy, radius int, alpha uint8) {
	drawRadial(img, cx-radius/4, cy-radius/4, radius, color.RGBA{R: 255, G: 255, B: 255, A: alpha})
	for y := cy - radius; y <= cy+radius; y++ {
		for x := cx - radius; x <= cx+radius; x++ {
			d := math.Hypot(float64(x-cx), float64(y-cy))
			if d > float64(radius)-1.4 || d < float64(radius)-3.5 {
				continue
			}
			blendAt(img, x, y, color.RGBA{R: 255, G: 255, B: 255, A: alpha + 30})
		}
	}
}

func drawRibbon(img *image.RGBA, x1, y1, x2, y2, width float64, c color.RGBA) {
	steps := 900
	for i := 0; i < steps; i++ {
		t := float64(i) / float64(steps-1)
		x := x1 + (x2-x1)*t
		y := y1 + (y2-y1)*t + math.Sin(t*math.Pi*2)*42
		drawRadial(img, int(x), int(y), int(width), c)
	}
}

func blendAt(img *image.RGBA, x, y int, src color.RGBA) {
	if !image.Pt(x, y).In(img.Bounds()) || src.A == 0 {
		return
	}
	dst := img.RGBAAt(x, y)
	a := float64(src.A) / 255
	img.SetRGBA(x, y, color.RGBA{
		R: uint8(float64(src.R)*a + float64(dst.R)*(1-a)),
		G: uint8(float64(src.G)*a + float64(dst.G)*(1-a)),
		B: uint8(float64(src.B)*a + float64(dst.B)*(1-a)),
		A: 255,
	})
}

func mix(a, b color.RGBA, t float64) color.RGBA {
	lerp := func(x, y uint8) uint8 { return uint8(float64(x) + (float64(y)-float64(x))*t) }
	return color.RGBA{R: lerp(a.R, b.R), G: lerp(a.G, b.G), B: lerp(a.B, b.B), A: 255}
}
