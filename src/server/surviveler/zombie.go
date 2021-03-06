/*
 * Surviveler package
 * zombie entities
 */
package surviveler

import (
	"server/actions"
	"server/events"
	"time"

	"github.com/aurelien-rainone/gogeo/f32/d2"
)

/*
 * Possible zombie AI states.
 */
const (
	lookingState = iota
	walkingState
	attackingState
)

// TODO: all of those values should be taken from the zombie resource
const (
	zombieLookingInterval = 200 * time.Millisecond
	zombieDamageInterval  = 500 * time.Millisecond
	attackDistance        = 1.2
)

type Zombie struct {
	id          uint32
	g           *Game
	curState    int // current state
	combatPower uint8
	walkSpeed   float32
	totalHP     float32
	curHP       float32
	timeAcc     time.Duration
	target      Entity
	world       *World
	*Movable
}

func NewZombie(g *Game, pos d2.Vec2, walkSpeed float32, combatPower uint8, totalHP float32) *Zombie {
	return &Zombie{
		id:          InvalidID,
		g:           g,
		curState:    lookingState,
		walkSpeed:   walkSpeed,
		totalHP:     totalHP,
		curHP:       totalHP,
		combatPower: combatPower,
		world:       g.State().World(),
		Movable:     NewMovable(pos, walkSpeed),
	}
}

func (z *Zombie) Id() uint32 {
	return z.id
}

func (z *Zombie) SetId(id uint32) {
	z.id = id
}

func (z *Zombie) findPathToTarget() (Path, bool) {
	path, _, found := z.g.Pathfinder().FindPath(z.Pos, z.target.Position())
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
		if dist < attackDistance {
			state = attackingState
		} else {
			state = walkingState
		}
	}
	return
}

func (z *Zombie) walk(dt time.Duration) (state int) {
	state = z.curState

	dist := z.target.Position().Sub(z.Pos).Len()
	if dist < attackDistance {
		state = attackingState
		return
	}

	if z.timeAcc >= zombieLookingInterval {
		z.timeAcc -= zombieLookingInterval
		state = lookingState
		return
	}

	z.Speed = z.walkSpeed
	if collideState := z.moveOrCollide(dt); collideState != -1 {
		// next move would have collide, change to the collide state
		state = collideState
	}
	return
}

func (z *Zombie) attack(dt time.Duration) (state int) {
	state = z.curState

	if z.target.Position().Sub(z.Pos).Len() > attackDistance {
		state = walkingState
		return
	}

	if z.timeAcc >= zombieDamageInterval {
		z.timeAcc -= zombieDamageInterval
		if z.target.DealDamage(float32(z.combatPower)) {
			state = lookingState
		}
	}

	return
}

/*
 * moveOrCollide moves the zombies or resolve collision
 *
 * It returns the next zombie state, in order to resolve the possible collision
 * If -1 is returned, there was no collision and the zombie should go
 * ahead with its current action
 */
func (z *Zombie) moveOrCollide(dt time.Duration) (state int) {
	//func (z *Zombie) moveOrCollide(dt time.Duration) (hasCollided bool) {
	// check if moving would create a collision
	nextPos := z.Movable.ComputeMove(z.Pos, dt)
	nextBB := d2.RectFromCircle(nextPos, 0.5)
	colliding := z.world.AABBSpatialQuery(nextBB)

	var wouldCollide bool
	colliding.Each(func(e Entity) bool {

		if e == z {
			// it's just me... pass
			return true
		}
		if _, ok := e.(*Player); ok {
			// what? it's a player! let's kill him
			// change target, in case we were following somebody else
			state = attackingState
			z.target = e
			// we are colliding and the current framework allows us to 'resolve'
			// one collision only so no need to check further
			return false
		}
		state = lookingState
		wouldCollide = true
		return true
	})

	if !wouldCollide {
		if z.Movable.Move(dt) {
			z.world.UpdateEntity(z)
		}
		state = -1
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
		attackingState: z.attack,
	}

	nextState := stateMap[z.curState](dt)
	if nextState != z.curState {
		z.timeAcc = 0
		z.curState = nextState
	}
}

func (z *Zombie) Position() d2.Vec2 {
	return z.Pos
}

func (z *Zombie) Type() EntityType {
	return ZombieEntity
}

func (z *Zombie) State() EntityState {
	// first, compile the data depending on current action
	var actionData interface{} = actions.Idle{}
	var actionType actions.Type = actions.IdleId

	switch z.curState {
	case attackingState:
		actionData = actions.Attack{
			TargetID: z.target.Id(),
		}
		actionType = actions.AttackId

	case lookingState:
		fallthrough

	case walkingState:
		if !z.Movable.HasReachedDestination() {
			moveActionData := actions.Move{
				Speed: z.Speed,
			}
			actionType = actions.MoveId
			actionData = moveActionData
		}
	}

	return MobileEntityState{
		Type:         ZombieEntity,
		Xpos:         z.Pos[0],
		Ypos:         z.Pos[1],
		CurHitPoints: uint16(z.curHP),
		ActionType:   actionType,
		Action:       actionData,
	}
}

func (z *Zombie) findTarget() (Entity, float32) {
	ent, dist := z.g.State().NearestEntity(
		z.Pos,
		func(e Entity) bool {
			return e.Type() != ZombieEntity
		},
	)
	return ent, dist
}

func (z *Zombie) DealDamage(damage float32) (dead bool) {
	if damage >= z.curHP {
		z.curHP = 0
		z.g.PostEvent(events.NewEvent(
			events.ZombieDeathId,
			events.ZombieDeath{Id: z.id}))
		dead = true
	} else {
		z.curHP -= damage
	}
	return
}

func (z *Zombie) HealDamage(damage float32) (healthy bool) {
	// FIXME: healed zombies? No thanks.
	healthy = true
	return
}
