#=========================================================================
# GCD Unit RTL Model
#=========================================================================

from pymtl       import *
from pclib.ifcs  import InValRdyBundle, OutValRdyBundle, valrdy_to_str
from pclib.rtl   import Mux, RegEn, RegRst, Reg
from pclib.rtl   import LtComparator, ZeroComparator, Subtractor

from GcdUnitMsg  import GcdUnitReqMsg

#=========================================================================
# Constants
#=========================================================================

# *_MUX_SEL_X: a dont-care case. Make sure the output of MUX is ignored!

A_MUX_SEL_NBITS = 1
A_MUX_SEL_IN    = 0
A_MUX_SEL_SUB   = 1
A_MUX_SEL_X     = 0

B_MUX_SEL_NBITS = 1
B_MUX_SEL_IN    = 0
B_MUX_SEL_SUB   = 1
B_MUX_SEL_X     = 0

O_MUX_SEL_NBITS = 1
O_MUX_SEL_A     = 0
O_MUX_SEL_B     = 1
O_MUX_SEL_X     = 0

S_MUX_SEL_NBITS = 1
S_MUX_SEL_AB    = 0
S_MUX_SEL_BA    = 1
S_MUX_SEL_X     = 0

#=========================================================================
# GCD Unit RTL Datapath
#=========================================================================

class GcdUnitDpathRTL (Model):

  # Constructor

  def __init__( s ):

    #---------------------------------------------------------------------
    # Interface
    #---------------------------------------------------------------------

    s.req_msg_a  = InPort  (16)
    s.req_msg_b  = InPort  (16)
    s.resp_msg   = OutPort (16)

    # Control signals (ctrl -> dpath)

    s.a_mux_sel = InPort  (A_MUX_SEL_NBITS)
    s.a_reg_en  = InPort  (1)
    s.b_mux_sel = InPort  (B_MUX_SEL_NBITS)
    s.b_reg_en  = InPort  (1)
    s.o_mux_sel = InPort  (O_MUX_SEL_NBITS)
    s.s_mux_sel = InPort  (S_MUX_SEL_NBITS)

    # Status signals (dpath -> ctrl)

    s.is_a_zero = OutPort (1)
    s.is_b_zero = OutPort (1)
    s.is_a_lt_b = OutPort (1)

    #---------------------------------------------------------------------
    # Structural composition
    #---------------------------------------------------------------------

    # A mux

    s.sub_out   = Wire(16)
    s.b_reg_out = Wire(16)

    s.a_mux = m = Mux( 16, 2 )
    s.connect_pairs(
      m.sel,                  s.a_mux_sel,
      m.in_[ A_MUX_SEL_IN  ], s.req_msg_a,
      m.in_[ A_MUX_SEL_SUB ], s.sub_out,
    )

    # A register

    s.a_reg = m = RegEn(16)
    s.connect_pairs(
      m.en,  s.a_reg_en,
      m.in_, s.a_mux.out,
    )

    # B mux

    s.b_mux = m = Mux( 16, 2 )
    s.connect_pairs(
      m.sel,                  s.b_mux_sel,
      m.in_[ B_MUX_SEL_IN  ], s.req_msg_b,
      m.in_[ B_MUX_SEL_SUB ], s.sub_out,
    )

    # B register

    s.b_reg = m = RegEn(16)
    s.connect_pairs(
      m.en,  s.b_reg_en,
      m.in_, s.b_mux.out,
      m.out, s.b_reg_out,
    )

    # O mux

    s.o_mux = m = Mux( 16, 2 )
    s.connect_pairs(
      m.sel,                 s.o_mux_sel,
      m.in_[ O_MUX_SEL_A  ], s.a_reg.out,
      m.in_[ O_MUX_SEL_B  ], s.b_reg.out,
    )

    # S mux (minuend)

    s.minuend_mux = m = Mux( 16, 2 )
    s.connect_pairs(
      m.sel,                  s.s_mux_sel,
      m.in_[ S_MUX_SEL_AB  ], s.a_reg.out,
      m.in_[ S_MUX_SEL_BA  ], s.b_reg.out,
    )

    # S mux (subtrahend)

    s.subtrahend_mux = m = Mux( 16, 2 )
    s.connect_pairs(
      m.sel,                  s.s_mux_sel,
      m.in_[ S_MUX_SEL_AB  ], s.b_reg.out,
      m.in_[ S_MUX_SEL_BA  ], s.a_reg.out,
    )

    # A zero compare

    s.a_zero = m = ZeroComparator(16)
    s.connect_pairs(
      m.in_, s.a_reg.out,
      m.out, s.is_a_zero,
    )

    # B zero compare

    s.b_zero = m = ZeroComparator(16)
    s.connect_pairs(
      m.in_, s.b_reg.out,
      m.out, s.is_b_zero,
    )

    # Less-than comparator

    s.a_lt_b = m = LtComparator(16)
    s.connect_pairs(
      m.in0, s.a_reg.out,
      m.in1, s.b_reg.out,
      m.out, s.is_a_lt_b
    )

    # Subtractor

    s.sub = m = Subtractor(16)
    s.connect_pairs(
      m.in0, s.minuend_mux.out, 
      m.in1, s.subtrahend_mux.out,
      m.out, s.sub_out,
    )

    # connect to output port

    s.connect( s.o_mux.out, s.resp_msg )

#=========================================================================
# GCD Unit RTL Control
#=========================================================================

class GcdUnitCtrlRTL (Model):

  def __init__( s ):

    #---------------------------------------------------------------------
    # Interface
    #---------------------------------------------------------------------

    s.req_val    = InPort  (1)
    s.req_rdy    = OutPort (1)

    s.resp_val   = OutPort (1)
    s.resp_rdy   = InPort  (1)

    # Control signals (ctrl -> dpath)

    s.a_mux_sel = OutPort (A_MUX_SEL_NBITS)
    s.a_reg_en  = OutPort (1)
    s.b_mux_sel = OutPort (B_MUX_SEL_NBITS)
    s.b_reg_en  = OutPort (1)
    # select the output: is it reg_a or reg_b?
    s.o_mux_sel = OutPort (O_MUX_SEL_NBITS)
    # select minuend and subtrahend
    s.s_mux_sel = OutPort (S_MUX_SEL_NBITS)

    # Status signals (dpath -> ctrl)

    s.is_a_zero = InPort  (1)
    s.is_b_zero = InPort  (1)
    s.is_a_lt_b = InPort  (1)

    # State element

    s.STATE_IDLE = 0
    s.STATE_CALC = 1
    s.STATE_DONE = 2

    s.state = RegRst( 2, reset_value = s.STATE_IDLE )

    #---------------------------------------------------------------------
    # State Transition Logic
    #---------------------------------------------------------------------

    # flag indicating whether the computation is done
    s.is_finished   = Wire(1)

    @s.combinational
    def assign_is_finished():
      s.is_finished.value = s.is_a_zero or s.is_b_zero

    @s.combinational
    def state_transitions():

      curr_state = s.state.out
      next_state = s.state.out

      # Transistions out of IDLE state

      if ( curr_state == s.STATE_IDLE ):
        if ( s.req_val and s.req_rdy ):
          next_state = s.STATE_CALC

      # Transistions out of CALC state

      if ( curr_state == s.STATE_CALC ):
        if ( s.is_finished and s.resp_rdy and not s.req_val ): 
          next_state = s.STATE_IDLE
        elif ( s.is_finished and not ( s.resp_rdy and s.req_val ) ):
          next_state = s.STATE_DONE

      # Transistions out of DONE state

      if ( curr_state == s.STATE_DONE ):
        if ( s.resp_val and s.resp_rdy ):
          next_state = s.STATE_IDLE

      s.state.in_.value = next_state

    #---------------------------------------------------------------------
    # State Output Logic
    #---------------------------------------------------------------------

    s.do_swap   =   Wire(1)
    s.do_sub    =   Wire(1)

    # compute sel of A_MUX
    s.a_mux_sel_value   =   Wire(A_MUX_SEL_NBITS)

    @s.combinational
    def a_mux_set_val_gen():
      if ( ~s.is_finished ):
        # do_swap
        if ( s.is_a_lt_b ): 
          s.a_mux_sel_value.value = A_MUX_SEL_X
        # do_sub
        else: 
          s.a_mux_sel_value.value = A_MUX_SEL_SUB
      else:
        # be ready to accept next input
        if ( s.resp_rdy ): 
          s.a_mux_sel_value.value = A_MUX_SEL_IN
        # req_rdy will be 0, so dont care 
        else:
          s.a_mux_sel_value.value = A_MUX_SEL_X

    # compute sel of B_MUX
    s.b_mux_sel_value   =   Wire(B_MUX_SEL_NBITS)

    @s.combinational
    def b_mux_set_val_gen():
      if ( ~s.is_finished ):
        # do_swap
        if ( s.is_a_lt_b ): 
          s.b_mux_sel_value.value = B_MUX_SEL_SUB
        # do_sub
        else: 
          # dont-care since reg_b will be disabled 
          s.b_mux_sel_value.value = B_MUX_SEL_X
      else:
        # be ready to accept next input
        if ( s.resp_rdy ): 
          s.b_mux_sel_value.value = B_MUX_SEL_IN
        # req_rdy will be 0, so dont care 
        else:
          s.b_mux_sel_value.value = B_MUX_SEL_X

    @s.combinational
    def state_outputs():

      current_state = s.state.out

      # In IDLE state we simply wait for inputs to arrive and latch them

      if current_state == s.STATE_IDLE:
        s.req_rdy.value   = 1
        s.resp_val.value  = 0
        s.a_mux_sel.value = A_MUX_SEL_IN
        s.a_reg_en.value  = 1
        s.b_mux_sel.value = B_MUX_SEL_IN
        s.b_reg_en.value  = 1
        # s.resp_val = 0 so the output of O_MUX will be ignored
        s.o_mux_sel.value = O_MUX_SEL_X
        # a.en = 0 and b.en = 0 so the output of S_MUX will be ignored
        s.s_mux_sel.value = S_MUX_SEL_X

      # In CALC state we iteratively swap/sub to calculate GCD

      elif current_state == s.STATE_CALC:

        s.do_swap.value   = s.is_a_lt_b
        s.do_sub.value    = ~s.is_b_zero

        s.req_rdy.value   = s.is_finished and s.resp_rdy
        s.resp_val.value  = s.is_finished

        # see combinational block for cases where we need enable signal
        s.a_mux_sel.value = s.a_mux_sel_value
        s.a_reg_en.value  = ( ~s.is_finished and ~s.do_swap ) or \
                            ( s.is_finished and s.resp_rdy )

        s.b_mux_sel.value = s.b_mux_sel_value
        s.b_reg_en.value  = ( ~s.is_finished and s.do_swap ) or \
                            ( s.is_finished and s.resp_rdy )

        # choose whichever is not zero as output
        s.o_mux_sel.value = O_MUX_SEL_A if s.is_b_zero else O_MUX_SEL_B
        # if a < b then perform b - a
        s.s_mux_sel.value = S_MUX_SEL_BA if s.do_swap else S_MUX_SEL_AB

      # In DONE state we simply wait for output transaction to occur

      elif current_state == s.STATE_DONE:
        s.req_rdy.value   = 0
        s.resp_val.value  = 1
        s.a_mux_sel.value = A_MUX_SEL_X
        s.a_reg_en.value  = 0
        s.b_mux_sel.value = B_MUX_SEL_X
        s.b_reg_en.value  = 0
        # choose whichever is not zero as output
        s.o_mux_sel.value = O_MUX_SEL_A if s.is_b_zero else O_MUX_SEL_B
        # a.en = 0 and b.en = 0 so the output of S_MUX will be ignored
        s.s_mux_sel.value = S_MUX_SEL_X

#=========================================================================
# GCD Unit RTL Model
#=========================================================================

class GcdUnitRTL (Model):

  # Constructor

  def __init__( s ):

    # Interface

    s.req   = InValRdyBundle  ( GcdUnitReqMsg() )
    s.resp  = OutValRdyBundle ( Bits(16)        )

    # Instantiate datapath and control

    s.dpath = GcdUnitDpathRTL()
    s.ctrl  = GcdUnitCtrlRTL()

    # Connect input interface to dpath/ctrl

    s.connect( s.req.msg.a,       s.dpath.req_msg_a )
    s.connect( s.req.msg.b,       s.dpath.req_msg_b )

    s.connect( s.req.val,         s.ctrl.req_val    )
    s.connect( s.req.rdy,         s.ctrl.req_rdy    )

    # Connect dpath/ctrl to output interface

    s.connect( s.dpath.resp_msg,  s.resp.msg        )
    s.connect( s.ctrl.resp_val,   s.resp.val        )
    s.connect( s.ctrl.resp_rdy,   s.resp.rdy        )

    # Connect status/control signals

    s.connect_auto( s.dpath, s.ctrl )

  # Line tracing

  def line_trace( s ):

    state_str = "? "
    if s.ctrl.state.out == s.ctrl.STATE_IDLE:
      state_str = "I "
    if s.ctrl.state.out == s.ctrl.STATE_CALC:
      if s.ctrl.do_swap:
        state_str = "Cs"
      elif s.ctrl.do_sub:
        state_str = "C-"
      else:
        state_str = "C "
    if s.ctrl.state.out == s.ctrl.STATE_DONE:
      state_str = "D "

    return "{}({} {} {}){}".format(
      s.req,
      s.dpath.a_reg.out,
      s.dpath.b_reg.out,
      state_str,
      s.resp
    )

