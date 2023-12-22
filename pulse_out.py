"""
File:                       pulse_out.py

Library Call Demonstrated:  mcculw.ul.pulse_out_start()
                            mcculw.ul.pulse_out_stop()

Purpose:                    Controls an Output Timer Channel.

Demonstration:              Sends a frequency output to Timer 0.

Other Library Calls:        mcculw.ul.release_daq_device()

Special Requirements:       Device must have a Timer output.
"""

from __future__ import absolute_import, division, print_function
from builtins import *  # @UnusedWildImport

from time import sleep
from mcculw import ul
from mcculw.enums import CounterChannelType
from mcculw.device_info import DaqDeviceInfo
from mcculw.enums import InterfaceType

def config_first_detected_device(board_num, dev_id_list=None):
    """Adds the first available device to the UL.  If a types_list is specified,
    the first available device in the types list will be add to the UL.

    Parameters
    ----------
    board_num : int
        The board number to assign to the board when configuring the device.

    dev_id_list : list[int], optional
        A list of product IDs used to filter the results. Default is None.
        See UL documentation for device IDs.
    """

    ul.ignore_instacal()
    devices = ul.get_daq_device_inventory(InterfaceType.ANY)
    if not devices:
        raise Exception('Error: No DAQ devices found')

    print('Found', len(devices), 'DAQ device(s):')
    for device in devices:
        print('  ', device.product_name, ' (', device.unique_id, ') - ',
              'Device ID = ', device.product_id, sep='')

    device = devices[0]
    if dev_id_list:
        device = next((device for device in devices
                       if device.product_id in dev_id_list), None)
        if not device:
            err_str = 'Error: No DAQ device found in device ID list: '
            err_str += ','.join(str(dev_id) for dev_id in dev_id_list)
            raise Exception(err_str)

    # Add the first DAQ device to the UL with the specified board number
    ul.create_daq_device(board_num, device)

def pulse_begin(frequency: float, duty_cycle: float, timer_num: int):
    print('FREQ:', frequency, ',', 'DUTY:', duty_cycle, ',', 'TIMR:', timer_num)

    dev_id_list = []
    board_num = 0

    try:
        config_first_detected_device(board_num, dev_id_list)
        daq_dev_info = DaqDeviceInfo(board_num)
        
        if not daq_dev_info.supports_counters:
            raise Exception('ERROR: The DAQ device does not support counters.')
        
        print('\nActive DAQ device: ', daq_dev_info.product_name, ' (', daq_dev_info.unique_id, ')\n', sep='')

        ctr_info = daq_dev_info.get_ctr_info()

        # Find a pulse timer channel on the board.
        first_chan = next((channel for channel in ctr_info.chan_info
                           if channel.type == CounterChannelType.CTRPULSE),
                          None)

        if not first_chan:
            raise Exception('Error: The DAQ device does not support '
                            'pulse timers')
        
        # timer_num = first_chan.channel_num
        # frequency = (1.0 / (cadence_ms * 1e-3))
        # duty_cycle = (on_time_ns / (cadence_ms * 1e6))

        # Start the pulse timer output (optional parameters omitted)
        actual_frequency, actual_duty_cycle, _ = ul.pulse_out_start(
            board_num, timer_num, frequency, duty_cycle)

        print('\nRequested output:')
        print('%f Hz, %f duty ratio.'%(frequency, duty_cycle))
        print('%f ns on-time, %f ns (%f s) cadence.'%((1/frequency)*1e9*duty_cycle, (1/frequency)*1e9, (1/frequency)))

        # Print information about the output
        print('\nVerified output:')
        print('%f Hz, %f duty ratio.'%(actual_frequency, actual_duty_cycle))
        print('%f ns on-time, %f ns (%f s) cadence.'%((1/actual_frequency)*1e9*actual_duty_cycle, (1/actual_frequency)*1e9, (1/actual_frequency)))

    except Exception as e:
        print(e)
        raise Exception(e)
    finally:
        return board_num, timer_num 


def pulse_end(board_num, timer_num):
    # Stop the pulse timer output
    ul.pulse_out_stop(board_num, timer_num)
    print('Timer output stopped.')
    ul.release_daq_device(board_num)
        

    # Serial.println("\n[C] ---------------------- Charge Enable");
    # Serial.println("[F] ---------------------- Float Actuator");
    # Serial.println("[D] ---------------------- Discharge Enable");
    # Serial.println("[W] {Duration} {Delay} --- Increment Charge; Pulse Duration, Delay (mS)");
    # Serial.println("[S] {Duration} {Delay} --- Decrement Charge; Pulse Duration, Delay (mS)");

# TMR0 will be the Charge Enable pin.
# TMR1 will be the Discharge Enable pin.
# When 'enabled', will be outputting a PWM of 500 Hz @ 0.9999 duty ratio.

if __name__ == '__main__':
    command = 'N/A'
    status = 'FLOATING'
    notice = '\n'
    pulsing = False
    tmr0_live = False
    tmr1_live = False
    cadence_mode = True

    print('\nEnsure the following:')
    print('TMR0 ==> CHG_EN')
    print('TMR1 ==> DCHG_EN\n')

    TMR0: int = 0
    TMR1: int = 1

    CHG_EN: int = TMR0
    DCHG_EN: int = TMR1

    CD_FREQ = 500
    CD_DUTY = 0.9999

    # CADENCE INPUT MODE ==
    # FREQUENCY INPUT MODE 

    while(True):
        print('\n=== %s=================================='%('CADENCE INPUT MODE ==' if cadence_mode else 'FREQUENCY INPUT MODE '))
        print('[F] ---------------------------------- Float Actuator')
        print('[C] ---------------------------------- Charge Enable')
        print('[D] ---------------------------------- Discharge Enable')
        print('[W] {On-Time (ns)} ------------------- One-Shot Up-Pulse')
        print('[S] {On-Time (ns)} ------------------- One-Shot Down-Pulse')
        if cadence_mode:
            print('[WR] {On-Time (ns)} {Cadence (ms)} --- Repeated Up-Pulse')
            print('[SR] {On-Time (ns)} {Cadence (ms)} --- Repeated Down-Pulse')
        else:
            print('[WR] {Frequency (Hz)} {Duty Ratio} --- Repeated Up-Pulse')
            print('[SR] {Frequency (Hz)} {Duty Ratio} --- Repeated Down-Pulse')
        print('[R] ---------------------------------- Toggle Pulse Input Mode')
        print('[X] ---------------------------------- Special\n')

        print('\nPrevious command:    %s'%(command))
        print('Current status:      %s\n'%(status))

        print(notice)
        command = input('> ')
        toks = (command.strip()).split()

        if toks is None or len(toks) <= 0:
            notice = 'INPUT INVALID: Input blank.'
            continue
        
        if len(toks) == 2:
            _dist_ms = 1000
            frequency = (1.0 / ((_dist_ms * 1e-3)+(float(toks[1]) * 1e-9)))
            duty_cycle = (float(toks[1]) / (_dist_ms * 1e6))
        elif len(toks) == 3:
            if cadence_mode:
                frequency = (1.0 / (float(toks[2]) * 1e-3))
                duty_cycle = (float(toks[1]) / (float(toks[2]) * 1e6))
            else:
                frequency = float(toks[1])
                duty_cycle = float(toks[2])

        # Always end the previous pulse(s).
        if tmr0_live:
            pulse_end(board_num, TMR0)
            tmr0_live = False
        if tmr1_live:
            pulse_end(board_num, TMR1)
            tmr1_live = False

        if toks[0] == 'F' or toks[0] == 'f':
            # Nothing further to do.
            status = 'FLOATING'
            pass

        elif toks[0] == 'C' or toks[0] == 'c':
            tmr0_live = True
            board_num, timer_num = pulse_begin(CD_FREQ, CD_DUTY, CHG_EN)
            status = 'CHARGING'
            pass
        
        elif toks[0] == 'D' or toks[0] == 'd':
            tmr1_live = True
            board_num, timer_num = pulse_begin(CD_FREQ, CD_DUTY, DCHG_EN)
            status = 'DISCHARGING'
            pass
        
        elif toks[0] == 'W' or toks[0] == 'w':
            board_num, timer_num = pulse_begin(frequency, duty_cycle, CHG_EN)
            sleep(0.5)
            pulse_end(board_num, CHG_EN)
            status = 'FLOATING (PULSED UP %.1f ns)'%(float(toks[1]))
            pass
        
        elif toks[0] == 'S' or toks[0] == 's':
            board_num, timer_num = pulse_begin(frequency, duty_cycle, DCHG_EN)
            sleep(0.5)
            pulse_end(board_num, DCHG_EN)
            status = 'FLOATING (PULSED DOWN %.1f ns)'%(float(toks[1]))
            pass
        
        elif toks[0] == 'WR' or toks[0] == 'wr':
            tmr0_live = True
            board_num, timer_num = pulse_begin(frequency, duty_cycle, CHG_EN)
            status = 'REPEAT PULSING UP (%.2f Hz @ %f)'%(frequency, duty_cycle)
            pass
        
        elif toks[0] == 'SR' or toks[0] == 'sr':
            tmr1_live = True
            board_num, timer_num = pulse_begin(frequency, duty_cycle, DCHG_EN)
            status = 'REPEAT PULSING DOWN (%.2f Hz @ %f)'%(frequency, duty_cycle)
            pass
        
        elif toks[0] == 'R' or toks[0] == 'r':
            cadence_mode = not cadence_mode
            pass

        elif toks[0] == 'X':
            # Special stepping.

            print('Performing special stepping...')

            status = 'SPECIAL STEPPING'

            # Setup initial values.
            _dist_ms = 1000
            step_len_ns = 500
            frequency = (1.0 / ((_dist_ms * 1e-3)+step_len_ns * 1e-9))
            duty_cycle = (step_len_ns / (_dist_ms * 1e6))

            step_set_up = [500, 400, 200, 50, 50, 50, 50, 0, 0, 0, 0]
            step_set_dn = step_set_up.reverse() * -1

            # Charge to some initial value.
            for i in range(10):
                board_num, timer_num = pulse_begin(frequency, duty_cycle, CHG_EN)
                sleep(0.5)
                pulse_end(board_num, DCHG_EN)

                sleep(1)

            for _ in range(10):
                # Step up.
                for i in range(len(step_set_up)):
                    if step_set_up[i] == 0:
                        continue

                    frequency = (1.0 / ((_dist_ms * 1e-3)+step_set_up[i] * 1e-9))
                    duty_cycle = (step_set_up[i] / (_dist_ms * 1e6))

                    board_num, timer_num = pulse_begin(frequency, duty_cycle, CHG_EN)
                    sleep(0.5)
                    pulse_end(board_num, DCHG_EN)

                    sleep(1)

                # Step down.
                for i in range(len(step_set_dn)):
                    if step_set_dn[i] == 0:
                        continue

                    frequency = (1.0 / ((_dist_ms * 1e-3)+step_set_dn[i] * 1e-9))
                    duty_cycle = (step_set_dn[i] / (_dist_ms * 1e6))

                    board_num, timer_num = pulse_begin(frequency, duty_cycle, CHG_EN)
                    sleep(0.5)
                    pulse_end(board_num, DCHG_EN)

                    sleep(1)
            


        else:
            continue
        
        continue

        # This is the pulsing input menu loop.
        while(True):
            print('\n\n----------------------\n')
            print('Enter -2 to exit the pulse menu.')
            print('Enter -1 to switch input modes.')
        
            if pulsing:
                print('Pulsing: Enter 0 to cease pulsing.')
            else:
                print('Not pulsing.')
        
            if cadence_mode:
                print('CADENCE INPUT MODE')

                on_time = float(input('On-time (ns): '))

                if on_time == 0 and pulsing:
                    pulse_end(board_num, timer_num)
                    pulsing = False
                    continue
                elif on_time == -1:
                    cadence_mode = not cadence_mode
                    continue
                elif on_time == -2:
                    break

                cadence = float(input('Cadence (ms): '))

                if cadence == 0 and pulsing:
                    pulse_end(board_num, timer_num)
                    pulsing = False
                    continue
                elif cadence == -1:
                    cadence_mode = not cadence_mode
                    continue
                elif cadence == -2:
                    break

                frequency = (1.0 / (cadence * 1e-3))
                duty_cycle = (on_time / (cadence * 1e6))
            else:
                print('FREQUENCY INPUT MODE')

                frequency = float(input('Frequency (Hz): '))

                if frequency == 0 and pulsing:
                    pulse_end(board_num, timer_num)
                    pulsing = False
                    continue
                elif frequency == -1:
                    cadence_mode = not cadence_mode
                    continue
                elif frequency == -2:
                    break
                
                duty_cycle = float(input('Duty ratio: '))

                if duty_cycle == 0 and pulsing:
                    pulse_end(board_num, timer_num)
                    pulsing = False
                    continue
                elif duty_cycle == -1:
                    cadence_mode = not cadence_mode
                    continue
                elif duty_cycle == -2:
                    break
            
            if pulsing:
                pulse_end(board_num, timer_num)

            pulsing = True
            board_num, timer_num = pulse_begin(frequency, duty_cycle)


