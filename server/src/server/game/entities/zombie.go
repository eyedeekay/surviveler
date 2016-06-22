/*
 * Surviveler entity package
 * zombie
 */
package entities

import (
	"server/game"
	"server/game/components"
	"server/math"
	"time"
)

/*
 * Possible zombie AI states.
 */
const (
	lookingState = iota
	walkingState
	runningState
	attackingState
)

const (
	zombieLookingInterval    = 1 * time.Second
	zombieRunLookingInterval = 200 * time.Millisecond
	zombieDamageInterval     = 500 * time.Millisecond
	zombieWalkSpeed          = 1.0
	zombieRunSpeed           = 3.0
	rageDistance             = 4.0
	attackDistance           = 1.0
)

type Zombie struct {
	game     game.Game
	curState int // current state
	timeAcc  time.Duration
	target   game.Entity
	components.Movable
}

func NewZombie(game game.Game, pos math.Vec2) game.Entity {
	return &Zombie{
		game:     game,
		curState: lookingState,
		Movable: components.Movable{
			Speed: zombieWalkSpeed,
			Pos:   pos,
		},
	}
}

func (z *Zombie) findPathToTarget() (math.Path, bool) {
	path, _, found := z.game.GetPathfinder().FindPath(z.Pos, z.target.GetPosition())
	return path, found
}

func (z *Zombie) look(dt time.Duration) (state int) {
	state = z.curState

	ent, dist := z.findTarget()
	if ent != nil {
		// update the target
		z.target = ent

		path, found := z.findPathToTarget()
		if found == false {
			return
		}
		z.SetPath(path)

		// update the state
		if dist < rageDistance {
			state = runningState
		} else {
			state = walkingState
		}
	}
	return
}

func (z *Zombie) walk(dt time.Duration) (state int) {
	state = z.curState

	dist := z.target.GetPosition().Sub(z.Pos).Len()
	if dist < rageDistance {
		state = runningState
		return
	}

	if z.timeAcc >= zombieLookingInterval {
		z.timeAcc -= zombieLookingInterval
		state = lookingState
		return
	}

	z.Speed = zombieWalkSpeed
	z.Movable.Update(dt)

	return
}

func (z *Zombie) run(dt time.Duration) (state int) {
	state = z.curState

	if z.timeAcc >= zombieRunLookingInterval {
		z.timeAcc -= zombieRunLookingInterval

		path, found := z.findPathToTarget()
		if found == false {
			state = lookingState
			return
		}
		z.SetPath(path)
	}

	z.Speed = zombieRunSpeed
	z.Movable.Update(dt)

	if z.target.GetPosition().Sub(z.Pos).Len() <= attackDistance {
		state = attackingState
	}

	return
}

func (z *Zombie) attack(dt time.Duration) (state int) {
	state = z.curState

	if z.target.GetPosition().Sub(z.Pos).Len() > attackDistance {
		state = runningState
		return
	}

	if z.timeAcc >= zombieDamageInterval {
		z.timeAcc -= zombieDamageInterval
		// TODO: emit attacking events
	}

	return
}

func (z *Zombie) Update(dt time.Duration) {
	z.timeAcc += dt

	// TODO: check target entity existance; fallback to lookingState in case it
	// doesn't

	stateMap := map[int]func(time.Duration) int{
		lookingState:   z.look,
		walkingState:   z.walk,
		runningState:   z.run,
		attackingState: z.attack,
	}

	nextState := stateMap[z.curState](dt)
	if nextState != z.curState {
		z.timeAcc = 0
		z.curState = nextState
	}
}

func (z *Zombie) GetPosition() math.Vec2 {
	return z.Pos
}

func (z *Zombie) GetType() game.EntityType {
	return game.ZombieEntity
}

func (z *Zombie) GetState() game.EntityState {
	// first, compile the data depending on current action
	var actionData interface{} = game.IdleActionData{}
	var actionType game.ActionType = game.IdleAction

	switch z.curState {
	case lookingState:
		fallthrough
	case attackingState:
		// TODO: we are doing nothing here.
	case walkingState:
		fallthrough
	case runningState:
		if !z.Movable.HasReachedDestination() {
			moveActionData := game.MoveActionData{
				Speed: z.Speed,
				Path:  z.Movable.GetPath(maxWaypointsToSend),
			}
			actionType = game.MovingAction
			actionData = moveActionData
		}
	}

	return game.EntityState{
		Type:       game.ZombieEntity,
		Xpos:       float32(z.Pos[0]),
		Ypos:       float32(z.Pos[1]),
		ActionType: actionType,
		Action:     actionData,
	}
}

func (z *Zombie) findTarget() (game.Entity, float32) {
	ent, dist := z.game.GetState().GetNearestEntity(
		z.Pos,
		func(e game.Entity) bool {
			return e.GetType() != game.ZombieEntity
		},
	)
	return ent, dist
}