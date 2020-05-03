/* vim-autoimport as coc.nvim completion source */

const { sources, workspace, types } = require('coc.nvim');
const { nvim } = workspace;
const path = require('path');
const rtpPath = path.resolve(__dirname, '../');

// Type definitions:
// https://github.com/neoclide/coc.nvim/blob/master/src/types.ts

exports.activate = async (context) => {
  /**
   * Registers vim-autoimport's database as a coc.nvim completino source.
   */
  let { logger } = context;  // context: ExtensionContext
  await nvim.command(`source ${rtpPath}/autoload/autoimport.vim`);

  var cache = null;
  async function load_symbols() {
    if (!cache) {
      // load all data from autoimport manager. this can be very slow and block the UI.
      try {
        logger.info('Requesting the list of symbols...')
        cache = await nvim.call('py3eval', `vim_autoimport.get_manager().suggest(max_items=None)`)
        logger.info(`Updated symbols list, size = ${Object.keys(cache).length}`)
      }
      catch(e) {
        logger.error(e);
      }
    }
    return cache;
  };

  const shortcut = 'Imp';

  const source = {  // source: SourceConfig (ISource)
    name: 'autoimport',
    shortcut: shortcut,
    priority: 5,
    filetypes: ['python'],
    firstMatch: false,
    doComplete: async function (opt) {
      const { input } = opt;  // opt: CompleteOption
      var items = [];  // :help complete-items

      logger.info(`input = ${input}`);
      if (input.length < 1)
        return { items };

      var symbols = await load_symbols();
      Object.keys(symbols).forEach(key => {
        var packages = symbols[key];  // List[str]
        var menu = `[${shortcut}] ${packages[0]}`;
        if (packages.length > 1)
          menu += ` (${packages.length})`;
        items.push({  // VimCompleteItem
          word: key, menu: menu,
          info: packages.join('\n'),
        });
      });

      return { items };  // -> CompleteResult
    },

    refresh: async function () {
      // TODO: Refresh: invalidate the cache and reload data
    },

    onCompleteDone: async function (item, opt) {
      // When completion is accepted, we autoimport the symbol.
      // item: VimCompleteItem, opt: CompleteOption
      nvim.command(`ImportSymbol ${item.word}`);
    },

    // TODO: For `somepackage.someMethod`, `somepackage` should work as a qualifier
    //   e.g. tensorflow.Optimizer or tf.Optimizer => should rule out homonyms from other packages
    // TODO: make the completion continue after "dot"
  };

  context.subscriptions.push(sources.createSource(source));
};
