package game

import (
	"bitbucket.com/rookiegamedevs/surviveler/server/core"
	"bytes"
	"encoding/binary"
	"fmt"
	"net"
	"os"
	"os/signal"
	"runtime"
	"server/core"
	"syscall"
	"time"
)

const (
	CONN_HOST        = ""
	CONN_PORT        = "1234"
	MAX_OUT_CHANNELS = 100
	MAX_IN_CHANNELS  = 100
)

func StartGameServer() {
	runtime.GOMAXPROCS(runtime.NumCPU())

	// creates a tcp listener
	tcpAddr, err := net.ResolveTCPAddr("tcp4", CONN_HOST+":"+CONN_PORT)
	FatalError(err, "Resolving addr")
	listener, err := net.ListenTCP("tcp", tcpAddr)
	FatalError(err, "Listening TCP")

	// creates a server
	config := &core.ServerCfg{
		MaxOutgoingChannels: MAX_OUT_CHANNELS,
		MaxIncomingChannels: MAX_IN_CHANNELS,
	}
	srv := core.NewServer(config, &SurvCallback{}, &IncomingMsgReader{})

	// starts server (listening goroutine)
	go srv.Start(listener, time.Second)
	fmt.Println("listening:", listener.Addr())

	// catchs system signal
	chSig := make(chan os.Signal)
	signal.Notify(chSig, syscall.SIGINT, syscall.SIGTERM)
	fmt.Println("Signal: ", <-chSig)

	// stops server
	srv.Stop()
}

type SurvCallback struct {
	Addr net.Addr
}

func (this *SurvCallback) OnConnect(c *core.Conn) bool {

	this.Addr = c.GetRawConn().RemoteAddr()
	fmt.Println("OnConnect:", this.Addr)

	// start a goroutine that spams client with player position!
	go func() {
		var msg OutgoingMsg
		msg.Timestamp = 1234

		// create a buffer to contain a (X,Y) position: 2 x uint16 position: 4 Bytes
		var xpos, ypos uint16
		xpos = 10
		ypos = 15

		bbuf := bytes.NewBuffer(make([]byte, 0, 4))
		binary.Write(bbuf, binary.BigEndian, xpos)
		binary.Write(bbuf, binary.BigEndian, ypos)
		msg.Buffer = bbuf.Bytes()

		//msg.Buffer = []byte("Hello World")
		// Length is the buffer length + timestamp length
		msg.Length = uint16(len(msg.Buffer) + 8)
		for {
			switch {
			case c.IsClosed():
				return
			default:
				err := c.AsyncSendMessage(msg, time.Second)
				if err != nil {
					fmt.Printf("Error in AsyncSendMessage: %v\n", err)
				}
				fmt.Println("Sent msg in AsyncSendMessage")
				time.Sleep(200 * time.Millisecond)
			}
		}
	}()

	return true
}

func (this *SurvCallback) OnIncomingMsg(c *core.Conn, msg core.Message) bool {
	fmt.Println("OnIncomingMsg")
	return true
}

func (this *SurvCallback) OnClose(c *core.Conn) {
	fmt.Printf("OnClose(), conn.IsClosed() = %v\n", c.IsClosed())
}
