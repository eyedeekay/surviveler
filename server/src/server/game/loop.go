/*
 * Surviveler game package
 * game loop
 */

package game

import (
	log "github.com/Sirupsen/logrus"
	"runtime"
	"server/game/messages"
	"server/game/protocol"
	"time"
)

/*
 * loop is the main game loop, it fetches messages from a channel, processes
 * them immediately.
 */
func (g *Game) loop() {

	// will tick when it's time to send the gamestate to the clients
	sendTickChan := time.NewTicker(time.Millisecond * 100).C

	// will tick when it's time to update the game
	tickChan := time.NewTicker(time.Millisecond * 10).C

	// encapsulate the game state here, as it should not be accessed nor modified
	// from outside the game loop
	gs := NewGameState()

	msgmgr := new(protocol.MessageManager)
	msgmgr.Listen(messages.AddPlayerId, protocol.MsgHandlerFunc(gs.onAddPlayer))
	msgmgr.Listen(messages.MoveId, protocol.MsgHandlerFunc(gs.onMovePlayer))
	msgmgr.Listen(messages.DelPlayerId, protocol.MsgHandlerFunc(gs.onDelPlayer))

	// loop local stop condition
	quit := false

	var last_time, cur_time time.Time
	last_time = time.Now()

	go func() {
		for !quit {
			select {

			case <-g.loopCloseChan:
				quit = true

			case msg := <-g.msgChan:
				// dispatch msg to listeners
				if err := msgmgr.Dispatch(msg.Message, msg.ClientId); err != nil {
					log.WithField("err", err).Error("Dispatch returned an error")
				}

			case <-sendTickChan:

				// pack the gamestate into a message
				var msg *protocol.Message
				var err error
				if msg, err = gs.pack(); err != nil {
					log.WithField("err", err).Error("Couldn't pack the gamestate")
					quit = true
				}
				if msg != nil {
					g.server.Broadcast(msg)
				}

			case <-tickChan:

				// compute delta time
				cur_time = time.Now()
				dt := cur_time.Sub(last_time)

				// tick game: update entities
				for _, ent := range gs.players {
					ent.Update(dt)
				}
				last_time = cur_time

			default:

				// let the world spin
				runtime.Gosched()
			}
		}
		log.Info("Game just stopped ticking")
	}()
}
