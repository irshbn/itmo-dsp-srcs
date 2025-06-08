--------------------------------------------------------------------------------
--       ___  _________  _____ ______   ________     
--      |\  \|\___   ___\\   _ \  _   \|\   __  \    
--      \ \  \|___ \  \_\ \  \\\__\ \  \ \  \|\  \   
--       \ \  \   \ \  \ \ \  \\|__| \  \ \  \\\  \  
--        \ \  \   \ \  \ \ \  \    \ \  \ \  \\\  \ 
--         \ \__\   \ \__\ \ \__\    \ \__\ \_______\
--          \|__|    \|__|  \|__|     \|__|\|_______|
--      
--------------------------------------------------------------------------------
--! @copyright CERN-OHL-W-2.0
--
-- You may use, distribute and modify this code under the terms of the
-- CERN OHL v2 Weakly Reciprocal license. 
--
-- You should have received a copy of the CERN OHL v2 Weakly Reciprocal license
-- with this file. If not, please visit: https://cern-ohl.web.cern.ch/home
--------------------------------------------------------------------------------
--! @date June 8, 2025
--! @author Yaroslav Shubin <irshubin@itmo.ru>
--------------------------------------------------------------------------------
--! @brief Generic cascaded integrator-comb decimator
--------------------------------------------------------------------------------

library ieee;
use ieee.std_logic_1164.all;
use ieee.numeric_std.all;
use ieee.math_real.all;

entity cic_decimator is
  generic (
    cic_order : positive range 1 to 7 := 3; -- Filter order
    comb_taps : positive range 1 to 2 := 2; -- Differential comb delay
    dec_ratio : positive              := 64; -- Decimation ratio

    compensate : boolean := false; -- Enable compensator filter

    s_axis_data_width : positive := 1; -- Input bus width
    m_axis_data_width : positive := 12 -- Output bus width
  );
  port (
    aclk    : in std_logic;
    aresetn : in std_logic;

    s_axis_tready : out std_logic;
    s_axis_tvalid : in std_logic;
    s_axis_tdata  : in std_logic_vector(s_axis_data_width - 1 downto 0);

    m_axis_tready : in std_logic;
    m_axis_tvalid : out std_logic;
    m_axis_tdata  : out std_logic_vector(m_axis_data_width - 1 downto 0)
  );
end entity cic_decimator;

architecture rtl of cic_decimator is

  constant gain_bits   : natural := cic_order * natural(ceil(log2(real(comb_taps * dec_ratio))));
  constant input_bits  : natural := maximum(2, s_axis_data_width);
  constant min_regsize : natural := input_bits + gain_bits;

  type int_array_t is array (natural range <>) of signed(min_regsize - 1 downto 0);

  signal integrators : int_array_t(0 to cic_order);
  signal comb_dl     : int_array_t(0 to cic_order * (comb_taps + 1));
  signal fir_dl      : int_array_t(0 to 2 * cic_order - 1);

  signal fir_sum : signed(min_regsize - 1 downto 0);
  signal fir_neg : signed(min_regsize - 1 downto 0);

  signal dec_cnt : unsigned(find_leftmost(to_unsigned(maximum(dec_ratio - 1, cic_order + 1), 32), '1') downto 0);
  signal out_cnt : unsigned(find_leftmost(to_unsigned(cic_order + fir_dl'length + 1, 32), '1') downto 0);

begin
  assert m_axis_data_width >= min_regsize
  report "Output bus width is too short, output will be truncated"
    severity warning;
  --------------------------------------------------------------------------------
  -- Main process
  --------------------------------------------------------------------------------
  main_p : process (aclk)
  begin
    if rising_edge(aclk) then
      if aresetn = '0' then
        s_axis_tready <= '0';
        m_axis_tvalid <= '0';
        dec_cnt       <= to_unsigned(integrators'length, dec_cnt'length);
        out_cnt       <= to_unsigned(cic_order + fir_dl'length + 1, out_cnt'length) when compensate
          else to_unsigned(cic_order + 1, out_cnt'length);
        integrators <= (others => (others => '0'));
        comb_dl     <= (others => (others => '0'));
      else
        s_axis_tready <= '1';

        -- Handshake in
        if s_axis_tready = '1' and s_axis_tvalid = '1' then
          dec_cnt <= dec_cnt - 1;

          -- Input resizing
          integrators(integrators'low) <= resize(signed(s_axis_tdata), min_regsize) when s_axis_data_width > 1 else
          signed(resize(unsigned(s_axis_tdata), min_regsize));

          -- Integration
          for i in integrators'low + 1 to integrators'high loop
            integrators(i) <= integrators(i) + integrators(i - 1);
          end loop;
        end if;

        -- Decimation
        if dec_cnt = 0 then
          dec_cnt <= to_unsigned(dec_ratio - 1, dec_cnt'length);

          -- Comb-filtering
          comb_dl(comb_dl'low) <= integrators(integrators'high);
          for i in comb_dl'low + 1 to comb_dl'high loop
            if (i - comb_dl'low) mod (comb_taps + 1) = 0 then
              comb_dl(i) <= comb_dl(i - 1 - comb_taps) - comb_dl(i - 1);
            else
              comb_dl(i) <= comb_dl(i - 1);
            end if;
          end loop;

          if compensate then
            -- FIR compensator
            fir_dl  <= (comb_dl(comb_dl'high) sra gain_bits) & fir_dl(fir_dl'low to fir_dl'high - 1);
            fir_sum <= comb_dl(comb_dl'high) + fir_dl(fir_dl'high);

            case cic_order is
              when 1 =>
                fir_neg <= (fir_dl(comb_dl'low + cic_order - 1) sla 4) + (fir_dl(comb_dl'low + cic_order - 1) sla 1);

              when 2 to 3 =>
                fir_neg <= (fir_dl(comb_dl'low + cic_order - 1) sla 3) + (fir_dl(comb_dl'low + cic_order - 1) sla 1);

              when 4 to 5 =>
                fir_neg <= (fir_dl(comb_dl'low + cic_order - 1) sla 2) + (fir_dl(comb_dl'low + cic_order - 1) sla 1);

              when 6 to 7 =>
                fir_neg <= fir_dl(comb_dl'low + cic_order - 1) sla 2;

              when others =>
                null;
            end case;
          end if;

          -- Output gating
          if out_cnt /= 0 then
            out_cnt <= out_cnt - 1;
          else
            m_axis_tvalid <= '1';
            m_axis_tdata  <= std_logic_vector(resize(fir_sum - fir_neg, m_axis_data_width)) when compensate else
              std_logic_vector(resize(comb_dl(comb_dl'high), m_axis_data_width));
          end if;
        end if;

        -- Handshake out
        if m_axis_tready = '1' and m_axis_tvalid = '1' then
          m_axis_tvalid <= '0';
        end if;

      end if;
    end if;
  end process;

end architecture;